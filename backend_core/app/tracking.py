"""
Tracking router — customer-facing stage management endpoints.

Business logic lives in services/tracking_service.py.
Dashboard summary delegated to TrackingService.get_dashboard_summary().
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models, schemas
from .deps import get_current_user, get_db, require_role
from .services.tracking_service import TrackingService

router = APIRouter()

STAGE_ORDER = ["fabrication", "painting", "dispatch"]


# ---------------------------------------------------------------------------
# Serialisation helpers (used by this router and tracking_api.py)
# ---------------------------------------------------------------------------


def _capitalize_stage(s: str) -> str:
    return s.capitalize() if s else s


def _serialize_stage(row: models.StageTracking) -> schemas.StageStatusOut:
    return schemas.StageStatusOut.from_orm(row)


def _serialize_item_with_stages(item: models.ProductionItem, db: Session) -> schemas.ProductionItemWithStages:
    stages = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id).all()
    return schemas.ProductionItemWithStages(
        id=item.id,
        customer_id=item.customer_id,
        item_code=item.item_code,
        item_name=item.item_name,
        section=item.section,
        length_mm=item.length_mm,
        quantity=item.quantity,
        unit=item.unit,
        weight_per_unit=item.weight_per_unit,
        material_requirements=item.material_requirements,
        checklist=item.checklist,
        notes=item.notes,
        fabrication_deducted=item.fabrication_deducted,
        current_stage=item.current_stage,
        stages=[_serialize_stage(s) for s in stages],
    )


# ---------------------------------------------------------------------------
# Deprecated stage endpoints (V2 system handles this now)
# ---------------------------------------------------------------------------


@router.post("/start-stage", response_model=schemas.StageStatusOut)
def start_stage(
    action: schemas.StageAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    raise HTTPException(status_code=409, detail="Stage updates are managed via Tracking V2 system")


@router.post("/complete-stage", response_model=schemas.StageStatusOut)
def complete_stage(
    action: schemas.StageAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    raise HTTPException(status_code=409, detail="Stage updates are managed via Tracking V2 system")


# ---------------------------------------------------------------------------
# Customer tracking detail
# ---------------------------------------------------------------------------


@router.get("/customer/{customer_id}", response_model=schemas.CustomerTrackingOut)
def get_customer_tracking(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    cust = (
        db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    )
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    items_with = []
    all_stage_rows = []
    for item in cust.production_items:
        p = _serialize_item_with_stages(item, db)
        items_with.append(p)
        rows = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id).all()
        all_stage_rows.extend(rows)

    mu_rows = (
        db.query(models.MaterialUsage)
        .filter(models.MaterialUsage.customer_id == cust.id)
        .order_by(models.MaterialUsage.ts.desc())
        .all()
    )
    mu_serialized = [schemas.MaterialUsageOut.from_orm(m) for m in mu_rows]

    history_sorted = sorted(all_stage_rows, key=lambda x: x.started_at or x.completed_at or datetime.min, reverse=True)
    history_serialized = [_serialize_stage(r) for r in history_sorted]

    cur_stage = TrackingService.compute_customer_stage(db, cust)

    return schemas.CustomerTrackingOut(
        id=cust.id,
        name=cust.name,
        project=cust.project_details,
        current_stage=cur_stage,
        production_items=items_with,
        material_usage=mu_serialized,
        stage_history=history_serialized,
    )


# ---------------------------------------------------------------------------
# Compatibility list endpoint
# ---------------------------------------------------------------------------


@router.get("/customers", response_model=List[dict])
def list_customers_compat(
    name: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    item_name: Optional[str] = Query(None),
    item_code: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    stage_status: Optional[str] = Query(None),
    length_min: Optional[int] = Query(None),
    length_max: Optional[int] = Query(None),
    quantity_min: Optional[int] = Query(None),
    quantity_max: Optional[int] = Query(None),
    date_stage_from: Optional[str] = Query(None),
    date_stage_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    """Compatibility list endpoint extended with production-item & stage filters."""
    cust_query = db.query(models.Customer).filter(models.Customer.is_deleted == False)
    if name:
        cust_query = cust_query.filter(models.Customer.name.ilike(f"%{name}%"))
    if project:
        cust_query = cust_query.filter(models.Customer.project_details.ilike(f"%{project}%"))
    if date_from:
        try:
            cust_query = cust_query.filter(models.Customer.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            cust_query = cust_query.filter(models.Customer.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    has_item_filters = any(
        [
            item_name,
            item_code,
            section,
            stage,
            stage_status,
            length_min is not None,
            length_max is not None,
            quantity_min is not None,
            quantity_max is not None,
            date_stage_from,
            date_stage_to,
        ]
    )
    customers = cust_query.all()

    if not has_item_filters:
        return [
            {"id": c.id, "name": c.name, "current_stage": TrackingService.compute_customer_stage(db, c)}
            for c in customers
        ]

    # Build item/stage filters
    pi = models.ProductionItem
    st = models.StageTracking
    filters = []
    if item_name:
        filters.append(pi.item_name.ilike(f"%{item_name}%"))
    if item_code:
        filters.append(pi.item_code.ilike(f"%{item_code}%"))
    if section:
        filters.append(pi.section.ilike(f"%{section}%"))
    if length_min is not None:
        filters.append(pi.length_mm >= length_min)
    if length_max is not None:
        filters.append(pi.length_mm <= length_max)
    if stage:
        try:
            filters.append(func.lower(st.stage) == stage.lower())
        except Exception:
            filters.append(st.stage == stage)
    if stage_status:
        filters.append(st.status == stage_status)
    if date_stage_from:
        try:
            dsf = datetime.fromisoformat(date_stage_from)
            filters.append(or_(st.started_at >= dsf, st.completed_at >= dsf))
        except ValueError:
            pass
    if date_stage_to:
        try:
            dst = datetime.fromisoformat(date_stage_to)
            filters.append(or_(st.started_at <= dst, st.completed_at <= dst))
        except ValueError:
            pass

    base_cust_ids = [c.id for c in customers]
    if not base_cust_ids:
        return []

    q = db.query(func.distinct(pi.customer_id)).join(st, st.production_item_id == pi.id)
    q = q.filter(pi.customer_id.in_(base_cust_ids))
    if filters:
        q = q.filter(and_(*filters))
    matching_cust_ids = [r[0] for r in q.all()]

    if (quantity_min is not None) or (quantity_max is not None):
        mu_q = db.query(func.distinct(models.MaterialUsage.customer_id))
        if quantity_min is not None:
            mu_q = mu_q.filter(models.MaterialUsage.qty >= quantity_min)
        if quantity_max is not None:
            mu_q = mu_q.filter(models.MaterialUsage.qty <= quantity_max)
        mu_ids = [r[0] for r in mu_q.all()]
        matching_cust_ids = [cid for cid in matching_cust_ids if cid in mu_ids]

    selected_customers = (
        db.query(models.Customer)
        .filter(models.Customer.id.in_(matching_cust_ids), models.Customer.is_deleted == False)
        .all()
    )
    return [
        {"id": c.id, "name": c.name, "current_stage": TrackingService.compute_customer_stage(db, c)}
        for c in selected_customers
    ]


@router.get("/customers/{customer_id}", response_model=schemas.CustomerTrackingOut)
def get_customer_compat(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    return get_customer_tracking(customer_id, db, current_user)


@router.put("/customers/{customer_id}/stage")
def update_customer_stage_compat(
    customer_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    stage = payload.get("stage")
    action = payload.get("action")
    if stage not in STAGE_ORDER:
        raise HTTPException(status_code=400, detail="Invalid stage")
    cust = (
        db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    )
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    results = []
    for item in cust.production_items:
        try:
            if action == "started":
                idx = STAGE_ORDER.index(stage)
                if idx > 0:
                    prev = STAGE_ORDER[idx - 1]
                    prev_row = (
                        db.query(models.StageTracking)
                        .filter(
                            models.StageTracking.production_item_id == item.id,
                            models.StageTracking.stage == prev,
                            models.StageTracking.status == "completed",
                        )
                        .first()
                    )
                    if not prev_row:
                        continue
                inprog = (
                    db.query(models.StageTracking)
                    .filter(
                        models.StageTracking.production_item_id == item.id, models.StageTracking.status == "in_progress"
                    )
                    .first()
                )
                if inprog:
                    continue
                row = (
                    db.query(models.StageTracking)
                    .filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == stage)
                    .first()
                )
                now = datetime.utcnow()
                if row:
                    row.status = "in_progress"
                    row.started_at = now
                    row.updated_by = current_user.id
                else:
                    row = models.StageTracking(
                        production_item_id=item.id,
                        stage=stage,
                        status="in_progress",
                        started_at=now,
                        updated_by=current_user.id,
                    )
                    db.add(row)
                db.commit()
                db.refresh(row)
                results.append(_serialize_stage(row))
            elif action == "completed":
                row = (
                    db.query(models.StageTracking)
                    .filter(models.StageTracking.production_item_id == item.id, models.StageTracking.stage == stage)
                    .first()
                )
                if not row or row.status != "in_progress":
                    continue
                row.status = "completed"
                row.completed_at = datetime.utcnow()
                row.updated_by = current_user.id
                db.commit()
                db.refresh(row)
                results.append(_serialize_stage(row))
        except Exception:
            continue
    return {"updated": len(results), "details": [r.dict() for r in results]}


@router.post("/customers/{customer_id}/material-usage", response_model=schemas.MaterialUsageOut)
def post_material_usage(
    customer_id: int,
    mu: schemas.MaterialUsageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    cust = (
        db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    )
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    m = models.MaterialUsage(
        customer_id=customer_id,
        production_item_id=mu.production_item_id,
        name=mu.name,
        qty=mu.qty,
        unit=mu.unit,
        by=mu.by,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Production item CRUD
# ---------------------------------------------------------------------------


@router.get("/items/search", response_model=List[schemas.ProductionItemWithStages])
def search_production_items(
    search: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    stage: Optional[str] = Query(None),
    stage_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_archived == False,
        )
    )
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                models.ProductionItem.item_name.ilike(term),
                models.ProductionItem.item_code.ilike(term),
                models.ProductionItem.section.ilike(term),
            )
        )
    if customer_id:
        query = query.filter(models.ProductionItem.customer_id == customer_id)

    items = query.all()

    if stage or stage_status:
        filtered = []
        for item in items:
            sq = db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id)
            if stage:
                sq = sq.filter(func.lower(models.StageTracking.stage) == stage.lower())
            if stage_status:
                sq = sq.filter(models.StageTracking.status == stage_status)
            if sq.first():
                filtered.append(item)
        items = filtered

    return [_serialize_item_with_stages(item, db) for item in items]


@router.get("/items/{item_id}", response_model=schemas.ProductionItemWithStages)
def get_production_item(
    item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    item = db.query(models.ProductionItem).filter(models.ProductionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Production item not found")
    return _serialize_item_with_stages(item, db)


@router.put("/items/{item_id}", response_model=schemas.ProductionItemWithStages)
def update_production_item(
    item_id: int,
    update_data: schemas.ProductionItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    item = db.query(models.ProductionItem).filter(models.ProductionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Production item not found")
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_item_with_stages(item, db)


@router.put("/items/{item_id}/checklist")
def update_item_checklist(
    item_id: int,
    checklist: List[dict],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.ProductionItem).filter(models.ProductionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Production item not found")
    item.checklist = json.dumps(checklist)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": "Checklist updated", "checklist": checklist}


@router.put("/items/{item_id}/material-requirements")
def update_item_material_requirements(
    item_id: int,
    requirements: List[dict],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    item = db.query(models.ProductionItem).filter(models.ProductionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Production item not found")
    if item.fabrication_deducted:
        raise HTTPException(
            status_code=400,
            detail="Cannot update material requirements - fabrication already completed and materials deducted",
        )
    item.material_requirements = json.dumps(requirements)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": "Material requirements updated", "requirements": requirements}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return TrackingService.get_dashboard_summary(db)


# ---------------------------------------------------------------------------
# All-items (paginated) — used by the main tracking table
# ---------------------------------------------------------------------------


@router.get("/all-items", response_model=dict)
def get_all_tracking_items(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    page: int = Query(1),
    page_size: int = Query(50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    try:
        query = (
            db.query(models.ProductionItem)
            .join(models.Customer)
            .options(
                joinedload(models.ProductionItem.customer),
                selectinload(models.ProductionItem.stages),
            )
            .filter(
                models.Customer.is_deleted == False,
                models.ProductionItem.is_archived == False,
            )
            .order_by(models.ProductionItem.id.asc())
        )

        if company_id:
            query = query.filter(models.ProductionItem.customer_id == company_id)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    models.ProductionItem.item_name.ilike(term),
                    models.ProductionItem.item_code.ilike(term),
                    models.ProductionItem.section.ilike(term),
                    models.Customer.name.ilike(term),
                )
            )

        items = query.all()
        result = []

        for item in items:
            stage_map = {s.stage: s.status for s in item.stages}
            fab_status = stage_map.get("fabrication", "pending")
            paint_status = stage_map.get("painting", "pending")
            disp_status = stage_map.get("dispatch", "pending")

            if disp_status == "completed":
                current_stage = "Completed"
            elif disp_status == "in_progress" or paint_status == "completed":
                current_stage = "Dispatch"
            elif paint_status == "in_progress" or fab_status == "completed":
                current_stage = "Painting"
            else:
                current_stage = "Fabrication"

            if stage and current_stage.lower() != stage.lower():
                continue
            if status:
                current_status = stage_map.get(current_stage.lower(), "pending")
                if current_status != status:
                    continue

            checklist = []
            if item.checklist:
                try:
                    checklist = json.loads(item.checklist)
                except Exception:
                    pass

            result.append(
                {
                    "id": item.id,
                    "customer_id": item.customer_id,
                    "customer_name": item.customer.name if item.customer else "Unknown",
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "section": item.section,
                    "length_mm": item.length_mm,
                    "quantity": item.quantity or 1,
                    "unit": item.unit,
                    "current_stage": current_stage,
                    "weight_per_unit": item.weight_per_unit,
                    "fabrication_status": fab_status,
                    "painting_status": paint_status,
                    "dispatch_status": disp_status,
                    "checklist": checklist,
                    "notes": item.notes,
                    "fabrication_deducted": item.fabrication_deducted,
                    "material_requirements": item.material_requirements,
                }
            )

        total = len(result)
        start = (page - 1) * page_size
        paginated_items = result[start : start + page_size]

        return {"page": page, "page_size": page_size, "total": total, "items": paginated_items}

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
