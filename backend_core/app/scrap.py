"""
Scrap and Reusable Inventory Management — Thin Router
Delegates all business logic to services/scrap_service.py
"""

from datetime import datetime
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import models
from .deps import get_current_user, get_db, require_role
from .services.scrap_service import (
    ReusableStockService,
    ScrapAnalyticsService,
    ScrapService,
)

router = APIRouter()


# ============ Pydantic Schemas ============


class ScrapRecordCreate(BaseModel):
    material_name: str
    weight_kg: float
    reason_code: str  # cutting_waste, defect, damage, overrun, leftover
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    quantity: int = 1
    source_item_id: Optional[int] = None
    source_customer_id: Optional[int] = None
    dimensions: Optional[str] = None
    notes: Optional[str] = None


class ScrapRecordOut(BaseModel):
    id: int
    material_name: str
    weight_kg: float
    length_mm: Optional[float]
    width_mm: Optional[float]
    quantity: int
    reason_code: str
    source_item_id: Optional[int]
    source_customer_id: Optional[int]
    dimensions: Optional[str]
    notes: Optional[str]
    status: str
    scrap_value: Optional[float]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ReusableStockCreate(BaseModel):
    material_name: str
    dimensions: str
    weight_kg: float
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    quantity: int = 1
    source_item_id: Optional[int] = None
    source_customer_id: Optional[int] = None
    quality_grade: str = "A"
    notes: Optional[str] = None


class ReusableStockOut(BaseModel):
    id: int
    material_name: str
    dimensions: str
    weight_kg: float
    length_mm: Optional[float]
    width_mm: Optional[float]
    quantity: int
    source_item_id: Optional[int]
    source_customer_id: Optional[int]
    quality_grade: str
    notes: Optional[str]
    is_available: bool
    used_in_item_id: Optional[int]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Scrap Endpoints ============


@router.get("/records/", response_model=List[ScrapRecordOut])
@router.get("/records", response_model=List[ScrapRecordOut])
def list_scrap_records(
    status: Optional[str] = Query(None),
    reason_code: Optional[str] = Query(None),
    material_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all scrap records with optional filters"""
    return ScrapService.list_scrap_records(db, status=status, reason_code=reason_code, material_name=material_name)


@router.post("/records", response_model=ScrapRecordOut)
def create_scrap_record(
    data: ScrapRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Record new scrap material"""
    try:
        return ScrapService.create_scrap_record(
            db,
            material_name=data.material_name,
            weight_kg=data.weight_kg,
            reason_code=data.reason_code,
            user_id=current_user.id,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            quantity=data.quantity,
            source_item_id=data.source_item_id,
            source_customer_id=data.source_customer_id,
            dimensions=data.dimensions,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-csv")
async def upload_scrap_csv(
    file: UploadFile = File(...),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload CSV of scrap items after dispatch."""
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files supported")

    content = await file.read()

    try:
        if file.filename.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(content))
        else:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(BytesIO(content), encoding=encoding)
                    break
                except Exception:
                    continue
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    try:
        return ScrapService.bulk_import_csv(db, df, current_user.id, customer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/records/{record_id}/status")
def update_scrap_status(
    record_id: int,
    status: str,
    scrap_value: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "Store Keeper")),
):
    """Update scrap record status"""
    try:
        return ScrapService.update_scrap_status(db, record_id, status, scrap_value)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/records/{record_id}/return-to-inventory")
def return_scrap_to_inventory(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "Store Keeper")),
):
    """Return scrap back to main inventory (for reusable pieces)"""
    try:
        return ScrapService.return_to_inventory(db, record_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/records/{record_id}/move-to-reusable")
def move_to_reusable(
    record_id: int,
    quality_grade: str = "A",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Move scrap to reusable stock (for offcuts that can be used later)"""
    try:
        return ScrapService.move_to_reusable(db, record_id, quality_grade, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/records/{record_id}")
def delete_scrap_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Delete a scrap record (admin only)"""
    try:
        return ScrapService.delete_scrap_record(db, record_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============ Reusable Stock Endpoints ============


@router.get("/reusable", response_model=List[ReusableStockOut])
def list_reusable_stock(
    available_only: bool = Query(True),
    material_name: Optional[str] = Query(None),
    quality_grade: Optional[str] = Query(None),
    min_length: Optional[float] = Query(None),
    max_length: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List reusable stock items with filters"""
    return ReusableStockService.list_reusable_stock(
        db,
        available_only=available_only,
        material_name=material_name,
        quality_grade=quality_grade,
        min_length=min_length,
        max_length=max_length,
    )


@router.get("/reusable/find-match")
def find_matching_reusable(
    material_name: str,
    required_length_mm: float,
    tolerance_mm: float = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Find reusable stock that matches required dimensions (for backfill)"""
    return ReusableStockService.find_matching_reusable(db, material_name, required_length_mm, tolerance_mm)


@router.post("/reusable", response_model=ReusableStockOut)
def create_reusable_stock(
    data: ReusableStockCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add new reusable stock item"""
    try:
        return ReusableStockService.create_reusable_stock(
            db,
            material_name=data.material_name,
            dimensions=data.dimensions,
            weight_kg=data.weight_kg,
            user_id=current_user.id,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            quantity=data.quantity,
            source_item_id=data.source_item_id,
            source_customer_id=data.source_customer_id,
            quality_grade=data.quality_grade,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reusable/{stock_id}/use")
def use_reusable_stock(
    stock_id: int,
    production_item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark reusable stock as used in a production item"""
    try:
        return ReusableStockService.use_reusable_stock(db, stock_id, production_item_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reusable/{stock_id}/return-to-inventory")
def return_reusable_to_inventory(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "Store Keeper")),
):
    """Return reusable stock back to main inventory"""
    try:
        return ReusableStockService.return_to_inventory(db, stock_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reusable/{stock_id}/mark-scrap")
def mark_reusable_as_scrap(
    stock_id: int,
    reason: str = "unusable",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark reusable stock as scrap (when it can't be used)"""
    try:
        return ReusableStockService.mark_as_scrap(db, stock_id, reason, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/reusable/{stock_id}")
def delete_reusable_stock(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Delete reusable stock item"""
    try:
        return ReusableStockService.delete_reusable_stock(db, stock_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============ Analytics Endpoints ============


@router.get("/analytics")
def get_loss_analytics(
    days: int = Query(30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get loss analytics and KPIs for dashboard"""
    return ScrapAnalyticsService.calculate_scrap_analytics(db, days)


@router.get("/summary")
def get_scrap_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Quick summary for dashboard widgets"""
    return ScrapAnalyticsService.get_scrap_summary(db)


# ============ Bulk Actions ============


@router.post("/bulk-action")
def bulk_scrap_action(
    action: str,
    record_ids: List[int],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "Store Keeper")),
):
    """Perform bulk action on multiple scrap records"""
    try:
        return ScrapAnalyticsService.bulk_scrap_action(db, action, record_ids, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
