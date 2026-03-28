"""
Pydantic schemas for Scrap and Reusable Stock endpoints.
Extracted from scrap.py for better file organization.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ScrapRecordCreate(BaseModel):
    material_name: str
    weight_kg: float
    reason_code: str
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


class ScrapRecordUpdate(BaseModel):
    status: Optional[str] = None
    scrap_value: Optional[float] = None
    notes: Optional[str] = None


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
