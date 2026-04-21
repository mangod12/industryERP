"""
Steel Fabrication ERP v3 - Drawing-Based Production Models
==========================================================
Introduces hierarchical production tracking:
  Drawing → Assembly → Component → ComponentInstance

Key Features:
- Drawing-wise BOM with component-level material links
- Independent stage tracking per component instance
- Material reservation before fabrication, consumption on completion
- Immutable stage transition audit trail
- Drawing revision support (ECN workflow)

Coexists with v1 (models.py) and v2 (models_v2.py).
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Boolean,
    Numeric, Enum as SQLEnum, Index, CheckConstraint, UniqueConstraint,
    JSON
)
from sqlalchemy.orm import relationship, validates
from .db import Base


# =============================================================================
# ENUMS
# =============================================================================

class DrawingStatus(str, Enum):
    DRAFT = "draft"
    DETAILED = "detailed"
    CHECKED = "checked"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class ComponentStage(str, Enum):
    """Configurable stages — these are defaults."""
    CUTTING = "cutting"
    DRILLING = "drilling"
    FITTING = "fitting"
    WELDING = "welding"
    PAINTING = "painting"
    QC = "qc"
    DISPATCH = "dispatch"
    COMPLETED = "completed"


class ComponentStageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    REWORK = "rework"


class ReservationStatus(str, Enum):
    RESERVED = "reserved"
    ISSUED = "issued"
    CONSUMED = "consumed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class RevisionChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class DispositionAction(str, Enum):
    REWORK = "rework"
    SCRAP_REMAKE = "scrap_remake"
    USE_AS_IS = "use_as_is"
    CANCEL = "cancel"


# =============================================================================
# STAGE CONFIGURATION
# =============================================================================

class StageConfig(Base):
    """Configurable stage pipeline per project. If none defined, defaults apply."""
    __tablename__ = "v3_stage_configs"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    stage_name = Column(String(50), nullable=False)
    sequence = Column(Integer, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    requires_qa_hold = Column(Boolean, default=False)
    auto_deduct_material = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("customer_id", "stage_name", name="uq_stage_config_customer_stage"),
        Index("ix_stage_config_customer", "customer_id"),
    )


# Default stage sequence when no custom config exists
DEFAULT_STAGES = [
    {"stage_name": "cutting", "sequence": 1, "is_mandatory": True, "auto_deduct_material": True},
    {"stage_name": "drilling", "sequence": 2, "is_mandatory": False},
    {"stage_name": "fitting", "sequence": 3, "is_mandatory": True},
    {"stage_name": "welding", "sequence": 4, "is_mandatory": True},
    {"stage_name": "painting", "sequence": 5, "is_mandatory": True},
    {"stage_name": "qc", "sequence": 6, "is_mandatory": False, "requires_qa_hold": True},
    {"stage_name": "dispatch", "sequence": 7, "is_mandatory": True},
]


# =============================================================================
# DRAWING
# =============================================================================

class Drawing(Base):
    """
    A shop drawing — the primary production unit.
    Contains one or more assemblies, each with components.
    """
    __tablename__ = "v3_drawings"

    id = Column(Integer, primary_key=True, index=True)
    drawing_number = Column(String(100), nullable=False, index=True)
    revision = Column(String(10), default="A", nullable=False)
    title = Column(String(500), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    project_ref = Column(String(200), nullable=True)
    status = Column(SQLEnum(DrawingStatus), default=DrawingStatus.DRAFT, nullable=False)

    # Weights (auto-calculated from components)
    total_weight_kg = Column(Numeric(15, 3), default=0)
    completed_weight_kg = Column(Numeric(15, 3), default=0)

    # Tracking
    released_date = Column(DateTime, nullable=True)
    released_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assemblies = relationship("Assembly", back_populates="drawing", cascade="all, delete-orphan")
    customer = relationship("Customer", foreign_keys=[customer_id])
    revisions = relationship("DrawingRevision", back_populates="drawing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("drawing_number", "revision", "customer_id",
                         name="uq_drawing_number_rev_customer"),
        Index("ix_drawing_customer", "customer_id"),
        Index("ix_drawing_status", "status"),
    )


# =============================================================================
# ASSEMBLY (Main Mark)
# =============================================================================

class Assembly(Base):
    """
    A main mark / shipping mark within a drawing.
    One drawing may have multiple assembly types, each with a quantity.
    """
    __tablename__ = "v3_assemblies"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("v3_drawings.id"), nullable=False)
    mark_number = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    quantity_required = Column(Integer, default=1, nullable=False)
    quantity_complete = Column(Integer, default=0)
    total_weight_kg = Column(Numeric(15, 3), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drawing = relationship("Drawing", back_populates="assemblies")
    components = relationship("Component", back_populates="assembly", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("drawing_id", "mark_number", name="uq_assembly_drawing_mark"),
    )


# =============================================================================
# COMPONENT (Piece Mark)
# =============================================================================

class Component(Base):
    """
    An individual piece within an assembly.
    Links to material master or v1 inventory for deduction.
    """
    __tablename__ = "v3_components"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("v3_assemblies.id"), nullable=False)
    piece_mark = Column(String(100), nullable=False)
    profile_section = Column(String(200), nullable=False)
    grade = Column(String(50), nullable=True)
    length_mm = Column(Numeric(10, 1), nullable=True)
    width_mm = Column(Numeric(10, 1), nullable=True)
    thickness_mm = Column(Numeric(10, 2), nullable=True)
    quantity_per_assembly = Column(Integer, default=1, nullable=False)
    weight_each_kg = Column(Numeric(15, 3), nullable=False)

    # Material link (v2 material_master preferred, v1 inventory as fallback)
    material_id = Column(Integer, ForeignKey("material_master.id"), nullable=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assembly = relationship("Assembly", back_populates="components")
    instances = relationship("ComponentInstance", back_populates="component",
                             cascade="all, delete-orphan")
    material = relationship("MaterialMaster", foreign_keys=[material_id])

    __table_args__ = (
        UniqueConstraint("assembly_id", "piece_mark", name="uq_component_assembly_piece"),
        CheckConstraint("weight_each_kg > 0", name="ck_component_weight_positive"),
    )

    @property
    def total_quantity(self):
        """Total instances needed = qty_per_assembly * assembly.quantity_required"""
        if self.assembly:
            return self.quantity_per_assembly * self.assembly.quantity_required
        return self.quantity_per_assembly

    @property
    def total_weight_kg(self):
        return self.weight_each_kg * self.total_quantity


# =============================================================================
# COMPONENT INSTANCE (Physical Piece Tracking)
# =============================================================================

class ComponentInstance(Base):
    """
    Tracks each physical piece through production stages independently.
    If Assembly has qty=3 and Component has qty_per_assembly=2, there are 6 instances.
    """
    __tablename__ = "v3_component_instances"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(Integer, ForeignKey("v3_components.id"), nullable=False)
    instance_number = Column(Integer, nullable=False)
    serial_tag = Column(String(100), nullable=True, unique=True)

    # Current state
    current_stage = Column(String(50), default="cutting", nullable=False)
    stage_status = Column(SQLEnum(ComponentStageStatus),
                          default=ComponentStageStatus.PENDING, nullable=False)
    stage_updated_at = Column(DateTime, nullable=True)
    stage_updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Material traceability
    stock_lot_id = Column(Integer, ForeignKey("stock_lots.id"), nullable=True)
    heat_number = Column(String(100), nullable=True)

    # Completion
    is_completed = Column(Boolean, default=False)
    is_scrapped = Column(Boolean, default=False)
    scrap_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Material deduction tracking
    material_reserved = Column(Boolean, default=False)
    material_issued = Column(Boolean, default=False)
    material_consumed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    component = relationship("Component", back_populates="instances")
    stage_transitions = relationship("StageTransition", back_populates="component_instance",
                                     cascade="all, delete-orphan",
                                     order_by="StageTransition.transitioned_at")
    reservations = relationship("MaterialReservation", back_populates="component_instance")

    __table_args__ = (
        UniqueConstraint("component_id", "instance_number",
                         name="uq_instance_component_number"),
        Index("ix_instance_stage", "current_stage"),
        Index("ix_instance_component", "component_id"),
    )


# =============================================================================
# STAGE TRANSITION (Immutable Audit Log)
# =============================================================================

class StageTransition(Base):
    """
    Immutable record of every stage change for a component instance.
    Never updated or deleted — append only.
    """
    __tablename__ = "v3_stage_transitions"

    id = Column(Integer, primary_key=True, index=True)
    component_instance_id = Column(Integer, ForeignKey("v3_component_instances.id"), nullable=False)
    from_stage = Column(String(50), nullable=True)
    to_stage = Column(String(50), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    transitioned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    station = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)

    # Material deduction result (if deduction triggered at this transition)
    deduction_result = Column(JSON, nullable=True)

    # Relationships
    component_instance = relationship("ComponentInstance", back_populates="stage_transitions")

    __table_args__ = (
        Index("ix_transition_instance", "component_instance_id"),
        Index("ix_transition_time", "transitioned_at"),
    )


# =============================================================================
# MATERIAL RESERVATION
# =============================================================================

class MaterialReservation(Base):
    """
    Soft-locks stock for a component before fabrication.
    Lifecycle: RESERVED → ISSUED → CONSUMED (or RETURNED/CANCELLED)
    """
    __tablename__ = "v3_material_reservations"

    id = Column(Integer, primary_key=True, index=True)
    component_instance_id = Column(Integer, ForeignKey("v3_component_instances.id"), nullable=False)
    stock_lot_id = Column(Integer, ForeignKey("stock_lots.id"), nullable=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)

    reserved_weight_kg = Column(Numeric(15, 3), nullable=False)
    issued_weight_kg = Column(Numeric(15, 3), default=0)
    consumed_weight_kg = Column(Numeric(15, 3), default=0)
    returned_weight_kg = Column(Numeric(15, 3), default=0)

    status = Column(SQLEnum(ReservationStatus), default=ReservationStatus.RESERVED, nullable=False)

    reserved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reserved_at = Column(DateTime, default=datetime.utcnow)
    issued_at = Column(DateTime, nullable=True)
    consumed_at = Column(DateTime, nullable=True)

    # Link to v2 stock movement for audit trail
    issue_movement_id = Column(Integer, ForeignKey("stock_movements.id"), nullable=True)
    consume_movement_id = Column(Integer, ForeignKey("stock_movements.id"), nullable=True)

    remarks = Column(Text, nullable=True)

    # Relationships
    component_instance = relationship("ComponentInstance", back_populates="reservations")

    __table_args__ = (
        Index("ix_reservation_instance", "component_instance_id"),
        Index("ix_reservation_status", "status"),
        CheckConstraint("reserved_weight_kg > 0", name="ck_reservation_weight_positive"),
    )


# =============================================================================
# DRAWING REVISION (ECN Support)
# =============================================================================

class DrawingRevision(Base):
    """Tracks revisions to a drawing with BOM diff."""
    __tablename__ = "v3_drawing_revisions"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("v3_drawings.id"), nullable=False)
    from_revision = Column(String(10), nullable=False)
    to_revision = Column(String(10), nullable=False)
    revision_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text, nullable=True)
    received_from = Column(String(200), nullable=True)
    bom_diff = Column(JSON, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    drawing = relationship("Drawing", back_populates="revisions")
    changes = relationship("RevisionChange", back_populates="revision",
                           cascade="all, delete-orphan")


class RevisionChange(Base):
    """Individual component change within a revision."""
    __tablename__ = "v3_revision_changes"

    id = Column(Integer, primary_key=True, index=True)
    revision_id = Column(Integer, ForeignKey("v3_drawing_revisions.id"), nullable=False)
    change_type = Column(SQLEnum(RevisionChangeType), nullable=False)
    component_id = Column(Integer, ForeignKey("v3_components.id"), nullable=True)
    field_changed = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    disposition = Column(SQLEnum(DispositionAction), nullable=True)
    disposition_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    disposition_at = Column(DateTime, nullable=True)
    cost_impact = Column(Numeric(15, 2), default=0)

    # Relationships
    revision = relationship("DrawingRevision", back_populates="changes")
