"""
Steel Fabrication ERP v3 - Pydantic v2 Schemas
===============================================
Schemas for the Drawing-Based Production hierarchy:
  Drawing → Assembly → Component → ComponentInstance

Mirrors models_v3.py. Uses Pydantic v2 conventions:
- class Config: from_attributes = True on all Out schemas
- Type-union syntax: X | None instead of Optional[X]
- float used for Numeric/Decimal fields (Pydantic handles coercion)
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


# =============================================================================
# RE-EXPORTED ENUMS (string values, safe to use in request/response bodies)
# =============================================================================

# Import enum values so callers can reference them without importing models_v3
from .models_v3 import (
    DrawingStatus,
    ComponentStage,
    ComponentStageStatus,
    ReservationStatus,
    RevisionChangeType,
    DispositionAction,
)


# =============================================================================
# DRAWING SCHEMAS
# =============================================================================

class DrawingCreate(BaseModel):
    drawing_number: str = Field(..., description="Unique drawing number (e.g. DWG-001)")
    title: str | None = Field(None, description="Descriptive title of the drawing")
    customer_id: int = Field(..., description="ID of the owning customer")
    project_ref: str | None = Field(None, description="Project reference or PO number")
    notes: str | None = Field(None, description="Free-text notes")


class DrawingUpdate(BaseModel):
    title: str | None = None
    project_ref: str | None = None
    notes: str | None = None
    status: DrawingStatus | None = None


class AssemblyOut(BaseModel):
    """Forward-declared; full definition below."""

    id: int
    drawing_id: int
    mark_number: str
    description: str | None
    quantity_required: int
    quantity_complete: int
    total_weight_kg: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
    components: list[ComponentOut] = []

    class Config:
        from_attributes = True


class DrawingOut(BaseModel):
    id: int
    drawing_number: str
    revision: str
    title: str | None
    customer_id: int
    project_ref: str | None
    status: DrawingStatus
    total_weight_kg: float
    completed_weight_kg: float
    released_date: datetime | None
    released_by: int | None
    created_by: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Nested hierarchy
    assemblies: list[AssemblyOut] = []

    # Computed completion statistics
    component_count: int = Field(0, description="Total distinct component types")
    instance_count: int = Field(0, description="Total physical instances to produce")
    completed_instance_count: int = Field(0, description="Instances that reached dispatch")
    completion_pct: float = Field(0.0, description="Percentage complete (0-100)")

    class Config:
        from_attributes = True


class DrawingSummary(BaseModel):
    """Lightweight card/list view — no nested hierarchy."""

    id: int
    drawing_number: str
    revision: str
    title: str | None
    status: DrawingStatus
    total_weight_kg: float
    completed_weight_kg: float
    customer_name: str = Field("", description="Denormalised customer name for display")
    project_ref: str | None = Field(None, description="Project reference for display")
    component_count: int = Field(0, description="Total distinct component types")
    completion_pct: float = Field(0.0, description="Percentage complete (0-100)")

    class Config:
        from_attributes = True


# =============================================================================
# ASSEMBLY SCHEMAS
# =============================================================================

class AssemblyCreate(BaseModel):
    mark_number: str = Field(..., description="Main-mark / shipping-mark identifier")
    description: str | None = Field(None, description="Assembly description")
    quantity_required: int = Field(1, ge=1, description="Number of this assembly required")
    notes: str | None = Field(None, description="Free-text notes")


class AssemblyUpdate(BaseModel):
    description: str | None = None
    quantity_required: int | None = Field(None, ge=1)
    notes: str | None = None


# Full AssemblyOut is defined above (forward reference for DrawingOut)
# Re-open it here as a proper schema — the model above acts as canonical form.


# =============================================================================
# COMPONENT SCHEMAS
# =============================================================================

class ComponentCreate(BaseModel):
    piece_mark: str = Field(..., description="Piece-mark identifier within the assembly")
    profile_section: str = Field(..., description="Steel profile / section size (e.g. UC203x203x46)")
    grade: str | None = Field(None, description="Steel grade (e.g. S275, S355)")
    length_mm: float | None = Field(None, gt=0, description="Length in millimetres")
    width_mm: float | None = Field(None, gt=0, description="Width in millimetres (plates)")
    thickness_mm: float | None = Field(None, gt=0, description="Thickness in millimetres")
    quantity_per_assembly: int = Field(1, ge=1, description="Pieces per assembly unit")
    weight_each_kg: float = Field(..., gt=0, description="Unit weight in kilograms")
    material_id: int | None = Field(None, description="v2 MaterialMaster FK (preferred)")
    inventory_id: int | None = Field(None, description="v1 Inventory FK (fallback)")
    notes: str | None = Field(None, description="Free-text notes")


class ComponentUpdate(BaseModel):
    piece_mark: str | None = None
    profile_section: str | None = None
    grade: str | None = None
    length_mm: float | None = Field(None, gt=0)
    width_mm: float | None = Field(None, gt=0)
    thickness_mm: float | None = Field(None, gt=0)
    quantity_per_assembly: int | None = Field(None, ge=1)
    weight_each_kg: float | None = Field(None, gt=0)
    material_id: int | None = None
    inventory_id: int | None = None
    notes: str | None = None


class ComponentOut(BaseModel):
    id: int
    assembly_id: int
    piece_mark: str
    profile_section: str
    grade: str | None
    length_mm: float | None
    width_mm: float | None
    thickness_mm: float | None
    quantity_per_assembly: int
    weight_each_kg: float
    material_id: int | None
    inventory_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Computed instance stats
    instance_count: int = Field(0, description="Total physical instances for this component")
    instances_completed: int = Field(0, description="Instances that reached 'completed' stage")
    instances_in_progress: int = Field(0, description="Instances currently being processed")

    class Config:
        from_attributes = True


# =============================================================================
# COMPONENT INSTANCE SCHEMAS
# =============================================================================

class StageTransitionOut(BaseModel):
    id: int
    from_stage: str | None
    to_stage: str
    from_status: str | None
    to_status: str
    transitioned_at: datetime
    performed_by: int
    station: str | None
    remarks: str | None

    class Config:
        from_attributes = True


class ComponentInstanceOut(BaseModel):
    id: int
    instance_number: int
    serial_tag: str | None
    current_stage: str
    stage_status: ComponentStageStatus
    stage_updated_at: datetime | None
    is_completed: bool
    is_scrapped: bool
    material_reserved: bool
    material_issued: bool
    material_consumed: bool
    stock_lot_id: int | None
    heat_number: str | None

    class Config:
        from_attributes = True


class ComponentInstanceDetail(ComponentInstanceOut):
    """Full detail view: includes immutable stage transition audit trail."""

    stage_transitions: list[StageTransitionOut] = []

    class Config:
        from_attributes = True


# =============================================================================
# STAGE OPERATION SCHEMAS
# =============================================================================

class AdvanceStageRequest(BaseModel):
    component_instance_id: int = Field(..., description="ID of the instance to advance")
    target_stage: str | None = Field(
        None,
        description="Explicit target stage; defaults to next in the configured pipeline",
    )
    remarks: str | None = Field(None, description="Optional operator remarks")
    station: str | None = Field(None, description="Workstation or bay identifier")


class BatchAdvanceRequest(BaseModel):
    instance_ids: list[int] = Field(..., min_length=1, description="Instance IDs to advance together")
    target_stage: str | None = Field(
        None,
        description="Common target stage; defaults to next stage for each instance",
    )
    remarks: str | None = Field(None, description="Optional batch remarks")
    station: str | None = Field(None, description="Workstation or bay identifier")


class AdvanceStageResponse(BaseModel):
    instance_id: int
    from_stage: str | None
    to_stage: str
    deduction_result: dict[str, Any] | None = Field(
        None, description="Material deduction outcome if triggered at this transition"
    )


# =============================================================================
# MATERIAL OPERATION SCHEMAS
# =============================================================================

class ReserveMaterialsRequest(BaseModel):
    drawing_id: int = Field(..., description="Reserve materials for all instances on this drawing")


class IssueMaterialRequest(BaseModel):
    component_instance_id: int = Field(..., description="Instance receiving the material")
    stock_lot_id: int | None = Field(
        None, description="Specific stock lot to issue from; omit for auto-pick"
    )


class ReturnMaterialRequest(BaseModel):
    component_instance_id: int = Field(..., description="Instance returning unused material")
    weight_kg: float = Field(..., gt=0, description="Weight being returned in kilograms")
    reason: str | None = Field(None, description="Reason for return (e.g. overcut, design change)")


class MaterialReservationOut(BaseModel):
    id: int
    component_instance_id: int
    stock_lot_id: int | None
    reserved_weight_kg: float
    issued_weight_kg: float
    consumed_weight_kg: float
    status: ReservationStatus
    reserved_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# DRAWING IMPORT SCHEMAS
# =============================================================================

class DrawingExcelImportRequest(BaseModel):
    customer_id: int = Field(..., description="Customer to associate the imported drawing with")
    sheet_name: str | None = Field(
        None, description="Excel sheet name to parse; defaults to the first sheet"
    )


class DrawingExcelImportResponse(BaseModel):
    drawing_count: int = Field(..., description="Drawings created or updated")
    assembly_count: int = Field(..., description="Assemblies created or updated")
    component_count: int = Field(..., description="Components created or updated")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal import warnings")


# =============================================================================
# DRAWING PROGRESS & SUMMARY SCHEMAS
# =============================================================================

class DrawingProgress(BaseModel):
    drawing_id: int
    drawing_number: str
    stages: dict[str, int] = Field(
        default_factory=dict,
        description="Map of stage_name → instance count currently at that stage",
    )
    total_instances: int = Field(0, description="Total physical instances across all components")
    completed_instances: int = Field(0, description="Instances that have fully completed")
    pct_complete: float = Field(0.0, description="Completion percentage (0-100)")


class DrawingWeightSummary(BaseModel):
    """Lightweight weight rollup for a drawing — progress vs BOM."""
    drawing_id: int
    bom_weight_kg: float = Field(0.0, description="Total theoretical weight from BOM")
    reserved_weight_kg: float = Field(0.0, description="Currently soft-locked in reservations")
    consumed_weight_kg: float = Field(0.0, description="Confirmed consumed weight")
    waste_weight_kg: float = Field(0.0, description="Issued minus consumed (offcut / waste)")


# =============================================================================
# KANBAN SCHEMAS
# =============================================================================

class KanbanColumn(BaseModel):
    stage_name: str = Field(..., description="Stage represented by this column")
    count: int = Field(0, description="Number of instances in this stage")
    instances: list[ComponentInstanceOut] = Field(
        default_factory=list, description="Instances currently in this stage"
    )


class KanbanBoard(BaseModel):
    drawing_id: int | None = Field(
        None, description="Scoped to a single drawing when set; global board when None"
    )
    columns: list[KanbanColumn] = Field(default_factory=list, description="Ordered stage columns")


# =============================================================================
# DRAWING MATERIAL USAGE (items used per drawing)
# =============================================================================

class ComponentMaterialUsage(BaseModel):
    """Material usage for a single component type within a drawing."""
    piece_mark: str
    profile_section: str
    grade: str | None = None
    weight_each_kg: float
    total_instances: int
    instances_consumed: int
    instances_pending: int
    total_required_kg: float = Field(description="Total weight needed for all instances")
    total_consumed_kg: float = Field(description="Weight actually deducted so far")
    total_reserved_kg: float = Field(description="Weight reserved but not yet consumed")
    material_name: str | None = Field(None, description="Linked inventory/material name")
    stock_lot_numbers: list[str] = Field(default_factory=list, description="Lot numbers consumed from")
    heat_numbers: list[str] = Field(default_factory=list, description="Heat numbers for traceability")


class AssemblyMaterialUsage(BaseModel):
    """Material usage aggregated per assembly."""
    mark_number: str
    description: str | None = None
    quantity_required: int
    quantity_complete: int
    components: list[ComponentMaterialUsage] = Field(default_factory=list)
    subtotal_required_kg: float = 0
    subtotal_consumed_kg: float = 0


class DrawingMaterialSummary(BaseModel):
    """Complete material usage report for a drawing — answers 'what items were used?'"""
    drawing_id: int
    drawing_number: str
    revision: str
    customer_name: str | None = None
    status: str
    assemblies: list[AssemblyMaterialUsage] = Field(default_factory=list)
    total_bom_weight_kg: float = Field(description="Total weight from BOM")
    total_consumed_kg: float = Field(description="Total weight actually deducted")
    total_reserved_kg: float = Field(description="Total weight reserved")
    total_pending_kg: float = Field(description="Weight not yet reserved or consumed")
    consumption_pct: float = Field(description="% of BOM weight consumed")


# =============================================================================
# FORWARD-REFERENCE RESOLUTION
# =============================================================================
# Pydantic v2 resolves forward references automatically on first model use,
# but explicit rebuilds are required when models reference each other across
# the module before both classes are defined.

AssemblyOut.model_rebuild()
DrawingOut.model_rebuild()
ComponentOut.model_rebuild()
ComponentInstanceDetail.model_rebuild()
