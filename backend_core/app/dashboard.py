from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from . import models
from .deps import get_db, require_role

router = APIRouter()


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User"))):
    # Inventory totals
    invs = db.query(models.Inventory).all()
    inventory = []
    for i in invs:
        total = float(i.total or 0)
        used = float(i.used or 0)
        remaining = total - used
        inventory.append({
            "id": i.id,
            "name": i.name,
            "unit": i.unit,
            "total": total,
            "used": used,
            "remaining": remaining,
        })

    # Items per stage counts
    stage_counts = {"fabrication": 0, "painting": 0, "dispatch": 0, "completed": 0}

    # Exclude production items that belong to soft-deleted customers or are archived
    pis = (
        db.query(models.ProductionItem)
        .join(models.Customer, models.ProductionItem.customer_id == models.Customer.id)
        .filter(
            models.Customer.is_deleted == False,
            models.ProductionItem.is_archived == False
        )
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
            stage_counts['fabrication'] += qty
            continue
        
        stage_statuses = {s.stage: s.status for s in current_stages}
        
        # Check priority in reverse order
        if stage_statuses.get('dispatch') == 'completed':
            stage_counts['completed'] += qty
        elif stage_statuses.get('dispatch') == 'in_progress':
            stage_counts['dispatch'] += qty
        elif stage_statuses.get('painting') == 'in_progress':
            stage_counts['painting'] += qty
        elif stage_statuses.get('painting') == 'completed':
            stage_counts['dispatch'] += qty
        elif stage_statuses.get('fabrication') == 'in_progress':
            stage_counts['fabrication'] += qty
        elif stage_statuses.get('fabrication') == 'completed':
            stage_counts['painting'] += qty
        else:
            stage_counts['fabrication'] += qty

    return {"inventory": inventory, "stage_counts": stage_counts}
