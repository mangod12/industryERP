from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models
from .deps import get_current_user, get_db, require_role
from .models_v2 import (
    DispatchNote,
    DocumentStatus,
    GoodsReceiptNote,
    MaterialMaster,
    StockLot,
    StockMovement,
)
from .services.stock_valuation_service import StockValuationService

router = APIRouter()


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User")),
):
    # Inventory totals
    invs = db.query(models.Inventory).all()
    inventory = []
    for i in invs:
        total = float(i.total or 0)
        used = float(i.used or 0)
        remaining = total - used
        inventory.append(
            {
                "id": i.id,
                "name": i.name,
                "unit": i.unit,
                "total": total,
                "used": used,
                "remaining": remaining,
            }
        )

    # Items per stage counts
    stage_counts = {"fabrication": 0, "painting": 0, "dispatch": 0, "completed": 0}

    # Exclude production items that belong to soft-deleted customers or are archived
    pis = (
        db.query(models.ProductionItem)
        .join(models.Customer, models.ProductionItem.customer_id == models.Customer.id)
        .filter(models.Customer.is_deleted == False, models.ProductionItem.is_archived == False)
        .all()
    )
    for item in pis:
        if not item:
            continue

        qty = item.quantity or 1.0

        # Access relationship defined in models.py
        current_stages = item.stages

        if not current_stages:
            # Default to fabrication if no tracking
            stage_counts["fabrication"] += qty
            continue

        stage_statuses = {s.stage: s.status for s in current_stages}

        # Check priority in reverse order
        if stage_statuses.get("dispatch") == "completed":
            stage_counts["completed"] += qty
        elif stage_statuses.get("dispatch") == "in_progress":
            stage_counts["dispatch"] += qty
        elif stage_statuses.get("painting") == "in_progress":
            stage_counts["painting"] += qty
        elif stage_statuses.get("painting") == "completed":
            stage_counts["dispatch"] += qty
        elif stage_statuses.get("fabrication") == "in_progress":
            stage_counts["fabrication"] += qty
        elif stage_statuses.get("fabrication") == "completed":
            stage_counts["painting"] += qty
        else:
            stage_counts["fabrication"] += qty

    return {"inventory": inventory, "stage_counts": stage_counts}


@router.get("/enhanced-summary")
def get_enhanced_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Enhanced dashboard with number cards and recent activity."""

    # ---- 1. Total Stock Value (v2 lots) ----
    total_stock_value = 0.0
    try:
        summaries = StockValuationService.get_stock_value_summary(db, method="fifo")
        total_stock_value = sum(s.get("total_value", 0) for s in summaries)
    except Exception:
        pass

    # ---- 2. Pending GRNs (draft or submitted) ----
    pending_grn_count = (
        db.query(func.count(GoodsReceiptNote.id))
        .filter(GoodsReceiptNote.status.in_([DocumentStatus.DRAFT, DocumentStatus.SUBMITTED]))
        .scalar()
    ) or 0

    # ---- 3. Open Dispatches (not approved and not cancelled) ----
    open_dispatch_count = (
        db.query(func.count(DispatchNote.id))
        .filter(DispatchNote.status.notin_([DocumentStatus.APPROVED, DocumentStatus.CANCELLED]))
        .scalar()
    ) or 0

    # ---- 4. Production Completion % ----
    total_items = (
        db.query(func.count(models.ProductionItem.id))
        .join(models.Customer, models.ProductionItem.customer_id == models.Customer.id)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_archived == False,
        )
        .scalar()
    ) or 0

    completed_items = (
        db.query(func.count(models.ProductionItem.id))
        .join(models.Customer, models.ProductionItem.customer_id == models.Customer.id)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_archived == False,
            models.ProductionItem.is_completed == True,
        )
        .scalar()
    ) or 0

    completion_pct = round((completed_items / total_items * 100), 1) if total_items > 0 else 0.0

    # ---- 5. Scrap Rate ----
    inventory_items = db.query(models.Inventory).all()
    total_consumed = sum(float(i.used or 0) for i in inventory_items)

    total_scrap_weight = 0.0
    try:
        total_scrap_weight = float(db.query(func.coalesce(func.sum(models.ScrapRecord.weight_kg), 0)).scalar())
    except Exception:
        pass

    scrap_rate_pct = round((total_scrap_weight / total_consumed * 100), 1) if total_consumed > 0 else 0.0

    # ---- 6. Low Stock Alerts ----
    # v1 low stock: remaining < 15% of total
    low_stock_count = sum(
        1
        for item in inventory_items
        if (item.total or 0) > 0 and ((item.total or 0) - (item.used or 0)) / (item.total or 1) < 0.15
    )
    # Also check v2 MaterialMaster reorder levels
    v2_low_stock = 0
    try:
        materials_with_reorder = db.query(MaterialMaster).filter(MaterialMaster.reorder_level > 0).all()
        for mat in materials_with_reorder:
            current_qty = (
                db.query(func.coalesce(func.sum(StockLot.current_weight_kg), 0))
                .filter(StockLot.material_id == mat.id, StockLot.is_active == True)
                .scalar()
            )
            if float(current_qty) < float(mat.reorder_level):
                v2_low_stock += 1
    except Exception:
        pass
    total_low_stock = low_stock_count + v2_low_stock

    # ---- 7. Recent Activity (last 10 stock movements) ----
    recent_activity: List[Dict[str, Any]] = []
    try:
        recent_movements = db.query(StockMovement).order_by(StockMovement.created_at.desc()).limit(10).all()
        for mv in recent_movements:
            lot = db.query(StockLot).filter(StockLot.id == mv.stock_lot_id).first()
            mat_name = ""
            if lot:
                mat = db.query(MaterialMaster).filter(MaterialMaster.id == lot.material_id).first()
                mat_name = mat.name if mat else f"Lot #{lot.lot_number}"
            recent_activity.append(
                {
                    "movement_number": mv.movement_number,
                    "material": mat_name,
                    "type": mv.movement_type.value if mv.movement_type else str(mv.movement_type),
                    "weight_change_kg": float(mv.weight_change_kg),
                    "timestamp": mv.created_at.isoformat() if mv.created_at else None,
                    "reason": mv.reason,
                }
            )
    except Exception:
        pass

    # ---- Build response ----
    number_cards = [
        {
            "label": "Total Stock Value",
            "value": round(total_stock_value, 2),
            "unit": "INR",
            "trend": None,
            "badge": None,
        },
        {
            "label": "Pending GRNs",
            "value": pending_grn_count,
            "unit": None,
            "trend": None,
            "badge": "warning" if pending_grn_count > 0 else "success",
        },
        {
            "label": "Open Dispatches",
            "value": open_dispatch_count,
            "unit": None,
            "trend": None,
            "badge": "info" if open_dispatch_count > 0 else "success",
        },
        {
            "label": "Production Completion",
            "value": completion_pct,
            "unit": "%",
            "trend": None,
            "badge": None,
        },
        {
            "label": "Scrap Rate",
            "value": scrap_rate_pct,
            "unit": "%",
            "trend": None,
            "badge": "danger" if scrap_rate_pct > 5 else "success",
        },
        {
            "label": "Low Stock Alerts",
            "value": total_low_stock,
            "unit": None,
            "trend": None,
            "badge": "danger" if total_low_stock > 0 else "success",
        },
    ]

    return {
        "number_cards": number_cards,
        "recent_activity": recent_activity,
    }
