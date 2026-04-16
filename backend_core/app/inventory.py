from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy import inspect
from datetime import datetime

from . import models, schemas
from .deps import get_db, require_role, get_current_user

router = APIRouter()


@router.get("/", response_model=List[schemas.InventoryOut])
@router.get("", response_model=List[schemas.InventoryOut], include_in_schema=False)
def list_inventory(
    material_name: Optional[str] = Query(None, alias="material_name"),
    material_code: Optional[str] = Query(None, alias="material_code"),
    section: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    quantity_min: Optional[int] = Query(None),
    quantity_max: Optional[int] = Query(None),
    unit: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    print("DEBUG: list_inventory hit!")
    """
    List inventory with optional filters (all filters via query params).
    Empty / missing params return the full list.
    Filters are applied safely via SQLAlchemy expressions (no raw SQL).
    """
    query = db.query(models.Inventory)

    # name / material_name (partial, case-insensitive)
    if material_name:
        query = query.filter(models.Inventory.name.ilike(f"%{material_name}%"))

    # only apply filters that correspond to actual columns in the DB table
    try:
        inspector = inspect(db.bind)
        existing_cols = {c['name'] for c in inspector.get_columns(models.Inventory.__tablename__)}
    except Exception:
        existing_cols = set()

    # code
    if material_code and 'code' in existing_cols:
        query = query.filter(models.Inventory.code.ilike(f"%{material_code}%"))

    # section
    if section and 'section' in existing_cols:
        query = query.filter(models.Inventory.section.ilike(f"%{section}%"))

    # category
    if category and 'category' in existing_cols:
        query = query.filter(models.Inventory.category.ilike(f"%{category}%"))

    # unit exact match (if provided)
    if unit:
        query = query.filter(models.Inventory.unit == unit)

    # quantity filters operate on remaining = total - used
    rem_expr = (models.Inventory.total - models.Inventory.used)
    if quantity_min is not None:
        query = query.filter(rem_expr >= quantity_min)
    if quantity_max is not None:
        query = query.filter(rem_expr <= quantity_max)

    # date range: requires created_at column to exist in DB
    if (date_from or date_to) and 'created_at' in existing_cols:
        try:
            if date_from:
                dt_from = datetime.fromisoformat(date_from)
                query = query.filter(models.Inventory.created_at >= dt_from)
            if date_to:
                dt_to = datetime.fromisoformat(date_to)
                query = query.filter(models.Inventory.created_at <= dt_to)
        except ValueError:
            # ignore invalid dates instead of failing the whole request
            pass

    items = query.all()
    return items


@router.post("/", response_model=schemas.InventoryOut)
@router.post("", response_model=schemas.InventoryOut, include_in_schema=False)
def create_item(item_in: schemas.InventoryIn, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    """
    Create a new inventory item.
    
    IMPORTANT: This is a simplified model. For production steel industry use,
    see the improved models in models_v2.py and routers/inventory_v2.py
    """
    # Validate that used doesn't exceed total
    if item_in.used > item_in.total:
        raise HTTPException(
            status_code=400,
            detail="Used quantity cannot exceed total quantity"
        )
    
    if item_in.total < 0 or item_in.used < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantities cannot be negative"
        )

    # Prevent duplicate material names
    existing = db.query(models.Inventory).filter(models.Inventory.name == item_in.name.strip()).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Material '{item_in.name.strip()}' already exists in inventory"
        )
    
    # Only include optional fields if the DB table actually has those columns
    try:
        inspector = inspect(db.bind)
        existing_cols = {c['name'] for c in inspector.get_columns(models.Inventory.__tablename__)}
    except Exception:
        existing_cols = set()

    item_kwargs = dict(
        name=item_in.name.strip(),  # Sanitize input
        unit=item_in.unit.strip() if item_in.unit else None,
        total=item_in.total,
        used=item_in.used,
    )
    if 'code' in existing_cols:
        item_kwargs['code'] = getattr(item_in, 'code', None)
    if 'section' in existing_cols:
        item_kwargs['section'] = getattr(item_in, 'section', None)
    if 'category' in existing_cols:
        item_kwargs['category'] = getattr(item_in, 'category', None)

    try:
        item = models.Inventory(**item_kwargs)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create inventory item: {str(e)}"
        )


@router.put("/{item_id}", response_model=schemas.InventoryOut)
def update_item(item_id: int, item_in: schemas.InventoryIn, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    """
    Update an inventory item.
    
    WARNING: This does NOT create an audit trail. For production use,
    implement proper stock movement tracking as in inventory_service.py
    """
    # Validate input
    if item_in.used > item_in.total:
        raise HTTPException(
            status_code=400,
            detail="Used quantity cannot exceed total quantity"
        )
    
    if item_in.total < 0 or item_in.used < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantities cannot be negative"
        )
    
    # Use SELECT FOR UPDATE to prevent race conditions
    # Note: SQLite doesn't support this, but PostgreSQL/MySQL do
    try:
        i = db.query(models.Inventory).filter(
            models.Inventory.id == item_id
        ).with_for_update(nowait=True).first()
    except Exception:
        # Fallback for SQLite
        i = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    
    if not i:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Store old values for audit (in production, log this properly)
    old_total = i.total
    old_used = i.used
    
    i.name = item_in.name.strip() if item_in.name else i.name
    i.unit = item_in.unit.strip() if item_in.unit else i.unit
    
    # Validation: Restrict manual 'used' updates to Boss only (Audit)
    if i.used != item_in.used:
        if current_user.role != "Boss":
            raise HTTPException(
                status_code=403, 
                detail="Manual consumption adjustment is restricted to Boss (Audit only). Normal consumption is automatic via Production."
            )
        i.used = item_in.used
    
    # 'total' can be updated (Add Stock) by authorized roles
    i.total = item_in.total
    
    try:
        inspector = inspect(db.bind)
        existing_cols = {c['name'] for c in inspector.get_columns(models.Inventory.__tablename__)}
    except Exception:
        existing_cols = set()

    if 'code' in existing_cols:
        i.code = getattr(item_in, 'code', None)
    if 'section' in existing_cols:
        i.section = getattr(item_in, 'section', None)
    if 'category' in existing_cols:
        i.category = getattr(item_in, 'category', None)
    
    try:
        db.add(i)
        db.commit()
        db.refresh(i)
        
        # Log significant changes (TODO: implement proper audit logging)
        if old_total != i.total or old_used != i.used:
            print(f"[AUDIT] Item {item_id} updated by user {current_user.id}: "
                  f"total {old_total}->{i.total}, used {old_used}->{i.used}")
        
        return i
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update inventory item: {str(e)}"
        )


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    i = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(i)
    db.commit()
    return {"message": "deleted"}


@router.get("/stats/summary")
def get_inventory_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get comprehensive inventory statistics for dashboard.
    
    Returns:
    - Grand totals: total purchased, total consumed, current stock
    - Per-material breakdown
    - Low stock alerts
    - Recent consumption history
    """
    from sqlalchemy import func
    
    # Get all inventory items
    inventory_items = db.query(models.Inventory).all()
    
    # Calculate grand totals
    total_purchased = sum((item.total or 0) for item in inventory_items)
    total_consumed = sum((item.used or 0) for item in inventory_items)
    current_stock = total_purchased - total_consumed
    
    # Low stock threshold (10% of total)
    low_stock_items = []
    for item in inventory_items:
        available = (item.total or 0) - (item.used or 0)
        if item.total and available < (item.total * 0.1):
            low_stock_items.append({
                "id": item.id,
                "name": item.name,
                "total": item.total,
                "used": item.used,
                "available": available,
                "percentage_remaining": round((available / item.total) * 100, 1) if item.total else 0
            })
    
    # Per-material breakdown
    material_breakdown = []
    for item in inventory_items:
        available = (item.total or 0) - (item.used or 0)
        material_breakdown.append({
            "id": item.id,
            "name": item.name,
            "unit": item.unit,
            "total": item.total or 0,
            "used": item.used or 0,
            "available": available,
            "section": getattr(item, 'section', None),
            "category": getattr(item, 'category', None),
        })
    
    # Recent material usage (last 10)
    recent_usage = db.query(models.MaterialUsage).order_by(
        models.MaterialUsage.ts.desc()
    ).limit(10).all()
    
    recent_usage_list = [
        {
            "id": u.id,
            "name": u.name,
            "qty": u.qty,
            "unit": u.unit,
            "by": u.by,
            "timestamp": u.ts.isoformat() if u.ts else None,
        }
        for u in recent_usage
    ]
    
    return {
        "grand_totals": {
            "total_purchased_kg": round(total_purchased, 2),
            "total_consumed_kg": round(total_consumed, 2),
            "current_stock_kg": round(current_stock, 2),
            "utilization_percentage": round((total_consumed / total_purchased) * 100, 1) if total_purchased else 0,
        },
        "item_count": len(inventory_items),
        "low_stock_count": len(low_stock_items),
        "low_stock_items": low_stock_items,
        "material_breakdown": material_breakdown,
        "recent_usage": recent_usage_list,
    }


@router.post("/reset-consumed", status_code=200)
def reset_consumed(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))
):
    """
    Reset 'used' quantity to 0 for ALL inventory items.
    """
    # Reset used amount
    db.query(models.Inventory).update({models.Inventory.used: 0})
    
    # Log activity
    log = models.ActivityLog(
        action="RESET_CONSUMED",
        description="Reset Total Consumed (kg) for all items",
        user_id=current_user.id
    )
    db.add(log)
    db.commit()
    return {"message": "Total consumed quantity reset successfully"}


@router.post("/reset-stock", status_code=200)
def reset_stock(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))
):
    """
    Reset 'total' and 'used' quantity to 0 for ALL inventory items.
    Effectively clears the stock counts but keeps the item names.
    """
    db.query(models.Inventory).update({models.Inventory.total: 0, models.Inventory.used: 0})
    
    # Log activity
    log = models.ActivityLog(
        action="RESET_STOCK",
        description="Reset Total Stock (kg) for all items",
        user_id=current_user.id
    )
    db.add(log)
    db.commit()
    return {"message": "Total stock quantity reset successfully"}


@router.get("/dashboard-data")
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all dashboard data in a single call for optimal performance.
    Combines inventory stats, tracking stats, and recent activity.
    """
    from sqlalchemy import func
    
    # Inventory stats
    inventory_items = db.query(models.Inventory).all()
    total_purchased = sum((item.total or 0) for item in inventory_items)
    total_consumed = sum((item.used or 0) for item in inventory_items)
    
    # Tracking stats by stage (sum quantities for job counts)
    stage_counts = {}
    for stage in ["fabrication", "painting", "dispatch"]:
        # Sum quantities for items with this stage pending/in_progress
        pending_sum = db.query(func.coalesce(func.sum(models.ProductionItem.quantity), 0)).join(models.StageTracking).join(models.Customer).filter(
            models.StageTracking.stage == stage,
            models.StageTracking.status.in_(["pending", "in_progress"]),
            models.ProductionItem.is_archived == False,
            models.Customer.is_deleted == False
        ).scalar()
        
        completed_sum = db.query(func.coalesce(func.sum(models.ProductionItem.quantity), 0)).join(models.StageTracking).join(models.Customer).filter(
            models.StageTracking.stage == stage,
            models.StageTracking.status == "completed",
            models.ProductionItem.is_archived == False,
            models.Customer.is_deleted == False
        ).scalar()
        
        stage_counts[stage] = {
            "pending": int(pending_sum),
            "completed": int(completed_sum),
            "total": int(pending_sum) + int(completed_sum)
        }
    
    # Total completed (dispatch stage done) - sum quantities
    fully_completed = db.query(func.coalesce(func.sum(models.ProductionItem.quantity), 0)).join(models.StageTracking).join(models.Customer).filter(
        models.StageTracking.stage == "dispatch",
        models.StageTracking.status == "completed",
        models.ProductionItem.is_archived == False,
        models.Customer.is_deleted == False
    ).scalar()
    fully_completed = int(fully_completed)
    
    # Total items (sum of quantities, active only)
    total_items = db.query(func.coalesce(func.sum(models.ProductionItem.quantity), 0)).join(models.Customer).filter(
        models.ProductionItem.is_archived == False,
        models.Customer.is_deleted == False
    ).scalar()
    total_items = int(total_items)
    
    # Customers count (exclude soft-deleted)
    customer_count = db.query(models.Customer).filter(models.Customer.is_deleted == False).count()
    
    # Low stock items
    low_stock = []
    for item in inventory_items:
        available = (item.total or 0) - (item.used or 0)
        if item.total and available < (item.total * 0.15):  # 15% threshold
            low_stock.append({
                "name": item.name,
                "available": available,
                "total": item.total,
            })
    
    # Recent activity (stage changes) - active items only
    recent_stages = db.query(models.StageTracking).join(models.ProductionItem).join(models.Customer).filter(
        models.ProductionItem.is_archived == False,
        models.Customer.is_deleted == False
    ).order_by(
        models.StageTracking.id.desc()
    ).limit(10).all()
    
    # Recent system logs (resets, etc.)
    recent_logs = db.query(models.ActivityLog).order_by(
        models.ActivityLog.timestamp.desc()
    ).limit(5).all()

    recent_activity = []
    
    # Add stage activities
    for s in recent_stages:
        item = db.query(models.ProductionItem).filter(
            models.ProductionItem.id == s.production_item_id
        ).first()
        if item:
            recent_activity.append({
                "item_name": item.item_name,
                "stage": s.stage,
                "status": s.status,
                "timestamp": (s.completed_at or s.started_at).isoformat() if (s.completed_at or s.started_at) else None,
                "type": "tracking"
            })
            
    # Add log activities
    for log in recent_logs:
        recent_activity.append({
            "item_name": log.description,
            "stage": "System",
            "status": log.action.replace("RESET_", "RESET "),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "type": "log"
        })
    
    # Sort merged list by timestamp desc
    recent_activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    
    # JSON-compatible result
    return {
        "inventory": {
            "total_materials": len(inventory_items),
            "total_purchased_kg": round(total_purchased, 2),
            "total_consumed_kg": round(total_consumed, 2),
            "current_stock_kg": round(total_purchased - total_consumed, 2),
            "low_stock_count": len(low_stock),
            "low_stock_items": low_stock[:5],  # Top 5
        },
        "tracking": {
            "total_items": total_items,
            "fabrication": stage_counts.get("fabrication", {}),
            "painting": stage_counts.get("painting", {}),
            "dispatch": stage_counts.get("dispatch", {}),
            "fully_completed": fully_completed,
        },
        "customers": {
            "total": customer_count,
        },
        "recent_activity": recent_activity[:10], # Return top 10 combined
    }
