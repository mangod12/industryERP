from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from . import models
from .deps import get_db, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
    stages = {"fabrication": 0, "painting": 0, "dispatch": 0, "completed": 0}
    pis = db.query(models.ProductionItem).all()
    for p in pis:
        cs = (p.current_stage or '').lower()
        if cs in stages:
            stages[cs] += 1
        else:
            # treat unknown as fabrication by default
            stages['fabrication'] += 1

    return {"inventory": inventory, "stage_counts": stages}
