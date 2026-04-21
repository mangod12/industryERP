from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models
from .deps import get_db, require_role
from .tracking import _serialize_item_with_stages
import json
from datetime import datetime
from sqlalchemy.sql import func
from pydantic import BaseModel
import pandas as pd
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter()

from .services.tracking_service import TrackingService


class TrackingUpdateIn(BaseModel):
    is_checked: Optional[bool] = None
    stage: Optional[str] = None
    move_quantity: Optional[int] = None


class QuantityMoveIn(BaseModel):
    move_quantity: float


def _capitalize(s: Optional[str]):
    return s.capitalize() if s else s


# =========================
# ACTIVE TRACKING LIST
# =========================
@router.get("", response_model=List[dict])
def list_tracking(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "User")
    ),
):
    q = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == False,
        )
    )

    if search:
        q = q.filter(models.ProductionItem.item_name.ilike(f"%{search}%"))

    items = q.all()
    out = []

    for it in items:
        cs = (it.current_stage or "fabrication").lower()

        if stage and cs != stage.lower():
            continue

        st_row = (
            db.query(models.StageTracking)
            .filter(
                models.StageTracking.production_item_id == it.id,
                models.StageTracking.stage == cs,
            )
            .first()
        )

        out.append(
            {
                "id": it.id,
                "item_code": it.item_code,
                "item_name": it.item_name,
                "section": it.section,
                "customer_id": it.customer_id,
                "customer_name": it.customer.name if it.customer else None,
                "current_stage": _capitalize(cs),
                "is_checked": bool(st_row.is_checked) if st_row else False,
                "material_deducted": bool(it.material_deducted),
                "quantity": it.quantity,
                "weight_per_unit": it.weight_per_unit,
            }
        )

    return out


# =========================
# PAGINATED ALL ITEMS (fast endpoint to reduce payload)
# =========================
@router.get("/all-items")
def get_all_items(
    company_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "User")
    ),
):
    # Safety limits
    if page < 1:
        page = 1
    if page_size > 100:
        page_size = 100

    query = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(models.Customer.is_deleted == False)
    )

    if company_id:
        query = query.filter(models.ProductionItem.customer_id == company_id)

    # Only show active (not completed) items by default to match tracking list behaviour
    query = query.filter(models.ProductionItem.is_completed == False)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.ProductionItem.item_code.ilike(search_term))
            | (models.ProductionItem.item_name.ilike(search_term))
            | (models.ProductionItem.section.ilike(search_term))
        )

    # Sort by ID ascending — gives every item a permanent, stable position.
    # Split children get the next available ID, so they appear at the end.
    # Users can search by item_code to find related splits.
    query = query.order_by(models.ProductionItem.id.asc())

    total = query.count()

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    # Serialize full item objects (avoid N+1 client fetches)
    serialized = []
    for it in items:
        try:
            p = _serialize_item_with_stages(it, db)
            # p is a Pydantic model; convert to dict
            d = p.dict()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Serialization error for item %s: %s", it.id, e)
            # Fallback minimal serialization
            d = {
                "id": it.id,
                "customer_id": it.customer_id,
                "item_code": it.item_code,
                "item_name": it.item_name,
                "section": it.section,
                "quantity": it.quantity,
                "unit": it.unit,
                "material_requirements": it.material_requirements,
                "checklist": it.checklist,
                "notes": it.notes,
                "fabrication_deducted": bool(
                    getattr(it, "fabrication_deducted", False)
                ),
                "current_stage": it.current_stage
                or "fabrication",  # Ensure stage is present!
                "stages": [],
            }

        # Ensure customer name present for frontend
        try:
            d["customer_name"] = it.customer.name if it.customer else None
        except Exception:
            d["customer_name"] = None

        # Parse checklist if it's a JSON string
        try:
            if isinstance(d.get("checklist"), str) and d.get("checklist"):
                d["checklist"] = json.loads(d["checklist"])
        except Exception:
            # leave as-is on parse failure
            pass

        serialized.append(d)

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": serialized,
    }


# =========================
# COMPLETED TRACKING
# =========================
@router.get("/completed")
def list_completed_tracking(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        # Show only recently completed (not archived) items and exclude deleted customers
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == False,
        )
        .order_by(models.ProductionItem.stage_updated_at.desc())
        .all()
    )

    return [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "section": it.section,
            "quantity": it.quantity,
            "current_stage": it.current_stage,
            "stage_updated_at": it.stage_updated_at,
            "customer": {"id": it.customer.id, "name": it.customer.name}
            if it.customer
            else None,
        }
        for it in items
    ]


# =========================
# DISPATCH EXCEL EXPORT
# =========================
@router.get("/export/dispatch")
def export_dispatch_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        # Export only completed but not archived items and exclude deleted customers
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == False,
        )
        .all()
    )

    if not items:
        raise HTTPException(status_code=404, detail="No completed items")

    rows = []
    for it in items:
        rows.append(
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Stage": "Dispatch",
                "Completed At": it.stage_updated_at,
            }
        )

    df = pd.DataFrame(rows)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dispatch Report")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dispatch_report.xlsx"},
    )


# =========================
# COMPLETED / ARCHIVED / COMPANY EXPORTS
# =========================
@router.get("/export/completed")
def export_completed_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == False,
        )
        .order_by(models.ProductionItem.stage_updated_at.desc())
        .all()
    )

    if not items:
        raise HTTPException(status_code=404, detail="No completed jobs found")

    rows = []
    for it in items:
        rows.append(
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Completed At": it.stage_updated_at,
            }
        )

    df = pd.DataFrame(rows)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Completed Jobs")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=completed_jobs.xlsx"},
    )


@router.get("/export/archived")
def export_archived_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == True,
        )
        .order_by(models.ProductionItem.stage_updated_at.desc())
        .all()
    )

    if not items:
        raise HTTPException(status_code=404, detail="No archived jobs found")

    rows = []
    for it in items:
        rows.append(
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Archived At": it.stage_updated_at,
            }
        )

    df = pd.DataFrame(rows)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Archived Jobs")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=archived_jobs.xlsx"},
    )


@router.get("/export/company")
def export_company_wise_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == False,
        )
        .order_by(models.Customer.name, models.ProductionItem.stage_updated_at)
        .all()
    )

    if not items:
        raise HTTPException(status_code=404, detail="No completed jobs found")

    rows = []
    for it in items:
        rows.append(
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Completed At": it.stage_updated_at,
            }
        )

    df = pd.DataFrame(rows)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Company Report")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=company_wise_report.xlsx"
        },
    )


# =========================
# UPDATE TRACKING ITEM
# =========================
@router.put("/{item_id}")
def update_tracking_item(
    item_id: int,
    payload: TrackingUpdateIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "Fabricator", "Painter", "Dispatch")
    ),
):
    try:
        # --- ROLE STAGE VALIDATION ---
        # Get the item to determine its current stage.
        # For checklist toggles, the action is on the *current* stage of the item.
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        cur_stage = (item.current_stage or "fabrication").lower()

        # If user is a specific stage operator, verify they are only interacting with their stage
        if current_user.role == "Fabricator" and cur_stage != "fabrication":
            raise HTTPException(
                status_code=403,
                detail="Fabricator can only update items in Fabrication stage",
            )
        elif current_user.role == "Painter" and cur_stage != "painting":
            raise HTTPException(
                status_code=403,
                detail="Painter can only update items in Painting stage",
            )
        elif current_user.role == "Dispatch" and cur_stage != "dispatch":
            raise HTTPException(
                status_code=403,
                detail="Dispatch can only update items in Dispatch stage",
            )

        # -------------------------
        # CHECKLIST TOGGLE
        # -------------------------
        if payload.is_checked is not None:
            TrackingService.toggle_checklist(
                db, item_id, payload.is_checked, current_user.id
            )

        # -------------------------
        # STAGE TRANSITION
        # -------------------------
        if payload.stage:
            TrackingService.advance_stage(
                db, item_id, payload.stage, current_user.id, payload.move_quantity
            )

        db.commit()  # Commit transaction after service operations
        return {"status": "updated"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================
# PARTIAL MOVE / SPLIT
# =========================
@router.post("/{item_id}/move-partial")
def move_partial_quantity(
    item_id: int,
    payload: QuantityMoveIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "Fabricator", "Painter", "Dispatch")
    ),
):
    try:
        res = TrackingService.split_item(db, item_id, payload.move_quantity)
        db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/archive")
def archive_completed_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    try:
        TrackingService.archive_item(db, item_id)
        return {"message": "Item archived successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/archived")
def list_archived_items(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    items = (
        db.query(models.ProductionItem)
        .join(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_completed == True,
            models.ProductionItem.is_archived == True,
        )
        .order_by(models.ProductionItem.stage_updated_at.desc())
        .all()
    )

    return [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "customer": it.customer.name if it.customer else None,
            "archived_at": it.stage_updated_at,
        }
        for it in items
    ]


# =========================
# ORDER VIEWS
# =========================
@router.get("/orders/active")
def list_active_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    return (
        db.query(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.Customer.order_status == "ACTIVE",
        )
        .all()
    )


@router.get("/orders/completed")
def list_completed_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    return (
        db.query(models.Customer)
        .filter(
            models.Customer.is_deleted == False,
            models.Customer.order_status == "COMPLETED",
        )
        .all()
    )


# =========================
# DRAWING-WISE TRACKING
# =========================
@router.get("/drawings")
def list_drawing_tracking(
    customer_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "User")
    ),
):
    """Return drawing-wise production tracking summary for the tracking page.

    Each drawing includes progress, stage breakdown, and component instance counts
    so the frontend can render drawing-based Kanban cards alongside the item-based view.
    """
    from .models_v3 import Drawing, DrawingStatus, Assembly, Component
    from sqlalchemy.orm import selectinload

    query = (
        db.query(Drawing)
        .options(
            selectinload(Drawing.assemblies)
            .selectinload(Assembly.components)
            .selectinload(Component.instances),
            selectinload(Drawing.customer),
        )
        .filter(Drawing.status.in_([
            DrawingStatus.RELEASED,
            DrawingStatus.IN_PROGRESS,
            DrawingStatus.COMPLETE,
        ]))
    )

    if customer_id:
        query = query.filter(Drawing.customer_id == customer_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Drawing.drawing_number.ilike(search_term))
            | (Drawing.title.ilike(search_term))
            | (Drawing.project_ref.ilike(search_term))
        )

    drawings = query.order_by(Drawing.created_at.desc()).limit(200).all()

    result = []
    for drawing in drawings:
        instances = [
            inst
            for assembly in drawing.assemblies
            for component in assembly.components
            for inst in component.instances
        ]
        total = len(instances)
        completed = sum(1 for inst in instances if inst.is_completed)
        scrapped = sum(1 for inst in instances if inst.is_scrapped)
        active = total - completed - scrapped

        # Stage breakdown for the drawing
        stage_counts = {}
        for inst in instances:
            if not inst.is_completed and not inst.is_scrapped:
                stage_counts[inst.current_stage] = stage_counts.get(inst.current_stage, 0) + 1

        # Determine overall drawing stage for Kanban placement
        if completed == total and total > 0:
            overall_stage = "completed"
        elif drawing.status == DrawingStatus.COMPLETE:
            overall_stage = "completed"
        elif stage_counts.get("dispatch", 0) > 0:
            overall_stage = "dispatch"
        elif stage_counts.get("painting", 0) > 0 or stage_counts.get("qc", 0) > 0:
            overall_stage = "painting"
        else:
            overall_stage = "fabrication"

        completion_pct = round((completed / total * 100), 1) if total > 0 else 0.0

        result.append({
            "id": drawing.id,
            "drawing_number": drawing.drawing_number,
            "revision": drawing.revision,
            "title": drawing.title,
            "customer_id": drawing.customer_id,
            "customer_name": drawing.customer.name if drawing.customer else "",
            "project_ref": drawing.project_ref,
            "status": drawing.status.value if drawing.status else "draft",
            "total_weight_kg": float(drawing.total_weight_kg or 0),
            "total_instances": total,
            "completed_instances": completed,
            "scrapped_instances": scrapped,
            "active_instances": active,
            "completion_pct": completion_pct,
            "stage_counts": stage_counts,
            "overall_stage": overall_stage,
            "assemblies": [
                {
                    "id": assembly.id,
                    "mark_number": assembly.mark_number,
                    "description": assembly.description,
                    "quantity_required": assembly.quantity_required,
                    "quantity_complete": assembly.quantity_complete,
                    "components": [
                        {
                            "id": comp.id,
                            "piece_mark": comp.piece_mark,
                            "profile_section": comp.profile_section,
                            "quantity_per_assembly": comp.quantity_per_assembly,
                            "weight_each_kg": float(comp.weight_each_kg or 0),
                            "instances": [
                                {
                                    "id": inst.id,
                                    "instance_number": inst.instance_number,
                                    "current_stage": inst.current_stage,
                                    "stage_status": inst.stage_status.value if inst.stage_status else "pending",
                                    "is_completed": inst.is_completed,
                                    "is_scrapped": inst.is_scrapped,
                                }
                                for inst in comp.instances
                            ],
                        }
                        for comp in assembly.components
                    ],
                }
                for assembly in drawing.assemblies
            ],
        })

    return result
