from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models, schemas
from .deps import get_db, require_role
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/api/tracking", tags=["tracking_api"])

STAGE_ORDER = ["fabrication", "painting", "dispatch"]
STAGE_FLOW = {"fabrication": "painting", "painting": "dispatch", "dispatch": None}


def _capitalize(s: Optional[str]):
    return s.capitalize() if s else s


class TrackingUpdateIn(BaseModel):
    is_checked: Optional[bool] = None
    stage: Optional[str] = None


@router.get("", response_model=List[dict])
def list_tracking(search: Optional[str] = Query(None), stage: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User"))):
    q = db.query(models.ProductionItem).join(models.Customer)
    if search:
        q = q.filter(models.ProductionItem.item_name.ilike(f"%{search}%"))
    items = q.all()
    out = []
    for it in items:
        cs = (it.current_stage or 'fabrication').lower()
        if stage and cs != stage.lower():
            continue
        # find stage row for current stage
        st_row = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == it.id, models.StageTracking.stage == cs).first()
        is_checked = False
        if st_row:
            is_checked = bool(getattr(st_row, 'is_checked', False))
        material_deducted = bool(getattr(it, 'material_deducted', False))
        out.append({
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "section": it.section,
            "customer_id": it.customer_id,
            "customer_name": it.customer.name if it.customer else None,
            "current_stage": _capitalize(cs),
            "is_checked": is_checked,
            "material_deducted": material_deducted
        })
    return out


@router.put("/{item_id}")
def update_tracking_item(item_id: int, payload: TrackingUpdateIn, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    item = db.query(models.ProductionItem).filter(models.ProductionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Production item not found")

    cur_stage = (item.current_stage or 'fabrication').lower()

    # Handle checklist toggle
    if payload.is_checked is not None:
        # ensure there is a StageTracking row for current stage
        st = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == cur_stage).first()
        if not st:
            # create row if missing
            st = models.StageTracking(production_item_id=item.id, stage=cur_stage, status='in_progress' if payload.is_checked else 'pending')
            db.add(st)
            db.commit()
            db.refresh(st)
        # If already checked and payload.is_checked True, no-op
        if not st.is_checked and payload.is_checked:
            # Mark checked and if fabrication, attempt material deduction now (only once)
            st.is_checked = True
            db.add(st)
            try:
                # Only attempt deduction for fabrication stage and if not already deducted on the item
                if cur_stage == 'fabrication' and not getattr(item, 'material_deducted', False):
                    # Begin nested transaction (savepoint) to allow safe rollback on partial failure
                    with db.begin_nested():
                        mu_rows = db.query(models.MaterialUsage).filter(models.MaterialUsage.production_item_id == item.id, models.MaterialUsage.applied == False).all()
                        for mu in mu_rows:
                            needed = float(mu.qty or 0)
                            # FIFO: consume from oldest inventory rows first
                            inv_rows = db.query(models.Inventory).filter(models.Inventory.name == mu.name).order_by(models.Inventory.created_at.asc(), models.Inventory.id.asc()).all()
                            if not inv_rows:
                                raise HTTPException(status_code=400, detail=f"Raw material '{mu.name}' not found in inventory; cannot check item")
                            for inv in inv_rows:
                                available = (inv.total or 0) - (inv.used or 0)
                                if available <= 0:
                                    continue
                                take = min(available, needed)
                                inv.used = (inv.used or 0) + float(take)
                                # record consumption for audit
                                cons = models.MaterialConsumption(material_usage_id=mu.id, inventory_id=inv.id, qty=float(take))
                                db.add(inv)
                                db.add(cons)
                                needed -= take
                                if needed <= 1e-9:
                                    break
                            if needed > 1e-9:
                                raise HTTPException(status_code=400, detail=f"Insufficient stock for material '{mu.name}' (need {mu.qty}, available less)")
                            mu.applied = True
                            db.add(mu)
                        # mark item as material deducted
                        item.material_deducted = True
                        db.add(item)
                # commit transaction happens on context exit
            except HTTPException:
                # Let HTTPExceptions bubble up unchanged
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to apply material deductions on checklist: {e}")
            # persist changes from nested transaction and staged updates
            db.commit()
        elif st.is_checked and not payload.is_checked:
            # allow un-checking at any time before completion
            st.is_checked = False
            db.add(st)
            db.commit()

    # Handle stage update (advance only)
    if payload.stage:
        requested = payload.stage.lower()
        # must be the next stage
        next_allowed = STAGE_FLOW.get(cur_stage)
        if next_allowed is None:
            # already at final
            raise HTTPException(status_code=400, detail="Item is already at final stage")
        if requested != next_allowed:
            raise HTTPException(status_code=400, detail=f"Stage update must advance to '{next_allowed}'")
        # require checklist checked before allowing advance
        st = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == cur_stage).first()
        if not st or not getattr(st, 'is_checked', False):
            raise HTTPException(status_code=400, detail="Checklist must be completed before advancing stage")

        # perform material deduction if moving from fabrication -> painting (ensure only once)
        try:
            if cur_stage == 'fabrication' and not getattr(item, 'material_deducted', False):
                # Perform FIFO deduction across inventory rows for each pending MaterialUsage
                with db.begin_nested():
                    mu_rows = db.query(models.MaterialUsage).filter(models.MaterialUsage.production_item_id == item.id, models.MaterialUsage.applied == False).all()
                    for mu in mu_rows:
                        needed = float(mu.qty or 0)
                        inv_rows = db.query(models.Inventory).filter(models.Inventory.name == mu.name).order_by(models.Inventory.created_at.asc(), models.Inventory.id.asc()).all()
                        if not inv_rows:
                            raise HTTPException(status_code=400, detail=f"Raw material '{mu.name}' not found in inventory; cannot advance")
                        for inv in inv_rows:
                            available = (inv.total or 0) - (inv.used or 0)
                            if available <= 0:
                                continue
                            take = min(available, needed)
                            inv.used = (inv.used or 0) + float(take)
                            cons = models.MaterialConsumption(material_usage_id=mu.id, inventory_id=inv.id, qty=float(take))
                            db.add(inv)
                            db.add(cons)
                            needed -= take
                            if needed <= 1e-9:
                                break
                        if needed > 1e-9:
                            raise HTTPException(status_code=400, detail=f"Insufficient stock for material '{mu.name}' (need {mu.qty}, available less)")
                        mu.applied = True
                        db.add(mu)
                    item.material_deducted = True
                    db.add(item)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to apply material deductions: {e}")

        # create/complete stage tracking rows and move item
        now = datetime.utcnow()
        # mark current stage row as completed
        cur_row = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == cur_stage).first()
        if cur_row:
            cur_row.status = 'completed'
            cur_row.completed_at = now
            db.add(cur_row)
        # create next stage row
        next_row = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == requested).first()
        if not next_row:
            next_row = models.StageTracking(production_item_id=item.id, stage=requested, status='pending')
            db.add(next_row)
        # update production item
        item.current_stage = requested
        item.stage_updated_at = now
        item.stage_updated_by = current_user.id
        db.add(item)
        # history
        try:
            hist = models.TrackingStageHistory(material_id=item.id, from_stage=cur_stage, to_stage=requested, changed_by=current_user.id, changed_at=now, remarks=None)
            db.add(hist)
        except Exception:
            pass
        db.commit()

    # return updated item
    st_row = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == item.current_stage).first()
    is_checked = bool(getattr(st_row, 'is_checked', False)) if st_row else False
    return {
        "id": item.id,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "section": item.section,
        "customer_id": item.customer_id,
        "current_stage": item.current_stage.capitalize() if item.current_stage else None,
        "is_checked": is_checked,
        "material_deducted": bool(getattr(item, 'material_deducted', False))
    }
