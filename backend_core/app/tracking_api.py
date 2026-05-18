"""
Tracking API router — list/export/archive endpoints.

Export logic delegated to services/export_service.py.
Business logic delegated to services/tracking_service.py.
Pydantic schemas live in schemas.py (TrackingUpdateIn, QuantityMoveIn).
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import models, schemas
from .deps import get_db, require_role
from .services.export_service import ExportService
from .services.tracking_service import TrackingService
from .tracking import _capitalize_stage, _serialize_item_with_stages

router = APIRouter()

logger = logging.getLogger(__name__)


# =========================
# ACTIVE TRACKING LIST
# =========================
@router.get("", response_model=List[dict])
def list_tracking(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
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
                "current_stage": _capitalize_stage(cs),
                "is_checked": bool(st_row.is_checked) if st_row else False,
                "material_deducted": bool(it.material_deducted),
                "quantity": it.quantity,
                "weight_per_unit": it.weight_per_unit,
            }
        )

    return out


# =========================
# PAGINATED ALL ITEMS
# =========================
@router.get("/all-items")
def get_all_items(
    company_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    if page < 1:
        page = 1
    if page_size > 100:
        page_size = 100

    query = db.query(models.ProductionItem).join(models.Customer).filter(models.Customer.is_deleted == False)

    if company_id:
        query = query.filter(models.ProductionItem.customer_id == company_id)

    query = query.filter(models.ProductionItem.is_completed == False)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.ProductionItem.item_code.ilike(search_term))
            | (models.ProductionItem.item_name.ilike(search_term))
            | (models.ProductionItem.section.ilike(search_term))
        )

    query = query.order_by(models.ProductionItem.id.asc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    serialized = []
    for it in items:
        try:
            p = _serialize_item_with_stages(it, db)
            d = p.dict()
        except Exception as e:
            logger.warning("Serialization error for item %s: %s", it.id, e)
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
                "fabrication_deducted": bool(getattr(it, "fabrication_deducted", False)),
                "current_stage": it.current_stage or "fabrication",
                "stages": [],
            }

        try:
            d["customer_name"] = it.customer.name if it.customer else None
        except Exception:
            d["customer_name"] = None

        try:
            if isinstance(d.get("checklist"), str) and d.get("checklist"):
                d["checklist"] = json.loads(d["checklist"])
        except Exception:
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
            "customer": {"id": it.customer.id, "name": it.customer.name} if it.customer else None,
        }
        for it in items
    ]


# =========================
# EXCEL EXPORTS (delegated to ExportService)
# =========================
@router.get("/export/dispatch")
def export_dispatch_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    output = ExportService.export_dispatch_excel(db)
    if output.getbuffer().nbytes == 0:
        raise HTTPException(status_code=404, detail="No completed items")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dispatch_report.xlsx"},
    )


@router.get("/export/completed")
def export_completed_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    output = ExportService.export_completed_excel(db)
    if output.getbuffer().nbytes == 0:
        raise HTTPException(status_code=404, detail="No completed jobs found")
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
    output = ExportService.export_archived_excel(db)
    if output.getbuffer().nbytes == 0:
        raise HTTPException(status_code=404, detail="No archived jobs found")
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
    output = ExportService.export_company_report(db)
    if output.getbuffer().nbytes == 0:
        raise HTTPException(status_code=404, detail="No completed jobs found")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=company_wise_report.xlsx"},
    )


# =========================
# UPDATE TRACKING ITEM
# =========================
@router.put("/{item_id}")
def update_tracking_item(
    item_id: int,
    payload: schemas.TrackingUpdateIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role("Boss", "Software Supervisor", "Fabricator", "Painter", "Dispatch")
    ),
):
    try:
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        cur_stage = (item.current_stage or "fabrication").lower()

        if current_user.role == "Fabricator" and cur_stage != "fabrication":
            raise HTTPException(status_code=403, detail="Fabricator can only update items in Fabrication stage")
        elif current_user.role == "Painter" and cur_stage != "painting":
            raise HTTPException(status_code=403, detail="Painter can only update items in Painting stage")
        elif current_user.role == "Dispatch" and cur_stage != "dispatch":
            raise HTTPException(status_code=403, detail="Dispatch can only update items in Dispatch stage")

        if payload.is_checked is not None:
            TrackingService.toggle_checklist(db, item_id, payload.is_checked, current_user.id)

        if payload.stage:
            TrackingService.advance_stage(db, item_id, payload.stage, current_user.id, payload.move_quantity)

        db.commit()
        return {"status": "updated"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================
# PARTIAL MOVE / SPLIT
# =========================
@router.post("/{item_id}/move-partial")
def move_partial_quantity(
    item_id: int,
    payload: schemas.QuantityMoveIn,
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
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    """Return drawing-wise production tracking summary."""
    from sqlalchemy.orm import selectinload

    from .models_v3 import Assembly, Component, Drawing, DrawingStatus

    query = (
        db.query(Drawing)
        .options(
            selectinload(Drawing.assemblies).selectinload(Assembly.components).selectinload(Component.instances),
            selectinload(Drawing.customer),
        )
        .filter(
            Drawing.status.in_(
                [
                    DrawingStatus.RELEASED,
                    DrawingStatus.IN_PROGRESS,
                    DrawingStatus.COMPLETE,
                ]
            )
        )
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
            inst for assembly in drawing.assemblies for component in assembly.components for inst in component.instances
        ]
        total = len(instances)
        completed = sum(1 for inst in instances if inst.is_completed)
        scrapped = sum(1 for inst in instances if inst.is_scrapped)
        active = total - completed - scrapped

        stage_counts = {}
        for inst in instances:
            if not inst.is_completed and not inst.is_scrapped:
                stage_counts[inst.current_stage] = stage_counts.get(inst.current_stage, 0) + 1

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

        result.append(
            {
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
            }
        )

    return result
