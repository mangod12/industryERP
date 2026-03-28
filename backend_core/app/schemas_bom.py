"""
Pydantic schemas for BOM (Bill of Materials) endpoints.
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Assembly Part schemas
# ---------------------------------------------------------------------------

class AssemblyPartCreate(BaseModel):
    mark_number: str
    part_name: str
    drawing_number: Optional[str] = None
    section: Optional[str] = None
    material_grade: Optional[str] = None
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    total_qty: int = 1
    weight_per_unit_kg: Optional[float] = None
    material_master_id: Optional[int] = None
    inventory_id: Optional[int] = None


class AssemblyPartUpdate(BaseModel):
    mark_number: Optional[str] = None
    part_name: Optional[str] = None
    drawing_number: Optional[str] = None
    section: Optional[str] = None
    material_grade: Optional[str] = None
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    total_qty: Optional[int] = None
    weight_per_unit_kg: Optional[float] = None
    material_master_id: Optional[int] = None
    inventory_id: Optional[int] = None


class AssemblyPartOut(BaseModel):
    id: int
    assembly_id: int
    mark_number: str
    part_name: str
    drawing_number: Optional[str] = None
    section: Optional[str] = None
    material_grade: Optional[str] = None
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    total_qty: int
    completed_qty: int = 0
    weight_per_unit_kg: Optional[float] = None
    total_weight_kg: Optional[float] = None
    material_master_id: Optional[int] = None
    inventory_id: Optional[int] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Assembly schemas
# ---------------------------------------------------------------------------

class AssemblyCreate(BaseModel):
    customer_id: int
    assembly_code: str
    assembly_name: str
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    ordered_qty: int = 1
    lot_number: Optional[str] = None
    notes: Optional[str] = None
    parts: Optional[List[AssemblyPartCreate]] = None


class AssemblyUpdate(BaseModel):
    assembly_name: Optional[str] = None
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    ordered_qty: Optional[int] = None
    lot_number: Optional[str] = None
    notes: Optional[str] = None


class AssemblyStageOut(BaseModel):
    id: int
    assembly_id: int
    stage: str
    status: str
    total_pieces: int = 0
    completed_pieces: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaterialRequirementOut(BaseModel):
    id: int
    assembly_id: int
    part_id: Optional[int] = None
    inventory_id: Optional[int] = None
    material_master_id: Optional[int] = None
    material_name: Optional[str] = None
    required_qty_kg: float
    deducted: bool = False

    class Config:
        from_attributes = True


class AssemblyOut(BaseModel):
    id: int
    customer_id: int
    assembly_code: str
    assembly_name: str
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    ordered_qty: int
    estimated_weight_kg: Optional[float] = None
    current_stage: str
    lot_number: Optional[str] = None
    fabrication_deducted: bool = False
    material_deducted: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parts: List[AssemblyPartOut] = []
    stage_tracking: List[AssemblyStageOut] = []

    class Config:
        from_attributes = True


class AssemblyListOut(BaseModel):
    """Lightweight assembly listing (no nested parts)."""
    id: int
    customer_id: int
    assembly_code: str
    assembly_name: str
    drawing_number: Optional[str] = None
    lot_number: Optional[str] = None
    ordered_qty: int
    estimated_weight_kg: Optional[float] = None
    current_stage: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Progress schemas
# ---------------------------------------------------------------------------

class StageProgress(BaseModel):
    stage: str
    total_pieces: int
    completed_pieces: int
    percentage: float = 0.0


class AssemblyProgress(BaseModel):
    assembly_id: int
    assembly_code: str
    assembly_name: str
    stages: List[StageProgress] = []


class ProgressDashboard(BaseModel):
    total_assemblies: int
    stages: List[StageProgress] = []
    assemblies: List[AssemblyProgress] = []


# ---------------------------------------------------------------------------
# CSV/Excel Import schemas
# ---------------------------------------------------------------------------

class CSVImportResult(BaseModel):
    assemblies_created: int = 0
    parts_created: int = 0
    errors: List[str] = []
    warnings: List[str] = []


class PieceCompletionUpdate(BaseModel):
    completed_delta: int = Field(..., description="Number of pieces completed in this batch")
