"""
BOM (Bill of Materials) Models for Steel Fabrication
=====================================================
Supports the assembly → parts → material requirements hierarchy
demonstrated by the handrail tracking sheet.

Key entities:
  - Assembly: Top-level fabricated structure (e.g., HR110 Handrail Type A)
  - AssemblyPart: Component part within an assembly (e.g., HR110-01 Top Rail)
  - AssemblyStageTracking: Per-stage progress with piece counts
  - AssemblyMaterialRequirement: Material needs per assembly/part
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Numeric,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class Assembly(Base):
    """Top-level fabricated structure."""

    __tablename__ = "assemblies"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    assembly_code = Column(String(50), nullable=False, index=True)
    assembly_name = Column(String(200), nullable=False)
    drawing_number = Column(String(100), nullable=True, index=True)
    revision = Column(String(20), nullable=True)
    ordered_qty = Column(Integer, nullable=False, default=1)
    estimated_weight_kg = Column(Numeric(15, 3), nullable=True)
    current_stage = Column(String(50), nullable=False, default="fabrication")
    lot_number = Column(String(50), nullable=True)
    fabrication_deducted = Column(Boolean, default=False)
    material_deducted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parts = relationship("AssemblyPart", back_populates="assembly", cascade="all, delete-orphan")
    stage_tracking = relationship("AssemblyStageTracking", back_populates="assembly", cascade="all, delete-orphan")
    material_requirements = relationship("AssemblyMaterialRequirement", back_populates="assembly", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("customer_id", "assembly_code", "lot_number", name="uq_assembly_customer_code_lot"),
        Index("ix_assembly_customer", "customer_id"),
        Index("ix_assembly_lot", "lot_number"),
    )


class AssemblyPart(Base):
    """Component part within an assembly."""

    __tablename__ = "assembly_parts"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    mark_number = Column(String(50), nullable=False)
    part_name = Column(String(200), nullable=False)
    drawing_number = Column(String(100), nullable=True)
    section = Column(String(100), nullable=True)
    material_grade = Column(String(50), nullable=True)
    length_mm = Column(Numeric(10, 2), nullable=True)
    width_mm = Column(Numeric(10, 2), nullable=True)
    thickness_mm = Column(Numeric(10, 3), nullable=True)
    total_qty = Column(Integer, nullable=False, default=1)
    completed_qty = Column(Integer, nullable=False, default=0)
    weight_per_unit_kg = Column(Numeric(15, 3), nullable=True)
    total_weight_kg = Column(Numeric(15, 3), nullable=True)
    material_master_id = Column(Integer, ForeignKey("material_master.id"), nullable=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assembly = relationship("Assembly", back_populates="parts")

    __table_args__ = (
        UniqueConstraint("assembly_id", "mark_number", name="uq_part_assembly_mark"),
        Index("ix_part_assembly", "assembly_id"),
    )


class AssemblyStageTracking(Base):
    """Per-stage progress with piece counts."""

    __tablename__ = "assembly_stage_tracking"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    stage = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    total_pieces = Column(Integer, nullable=False, default=0)
    completed_pieces = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    assembly = relationship("Assembly", back_populates="stage_tracking")

    __table_args__ = (
        UniqueConstraint("assembly_id", "stage", name="uq_assembly_stage"),
        Index("ix_assembly_stage_status", "assembly_id", "status"),
    )


class AssemblyMaterialRequirement(Base):
    """Material requirements per assembly/part — replaces JSON blob."""

    __tablename__ = "assembly_material_requirements"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("assembly_parts.id"), nullable=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    material_master_id = Column(Integer, ForeignKey("material_master.id"), nullable=True)
    material_name = Column(String(200), nullable=True)
    required_qty_kg = Column(Numeric(15, 3), nullable=False)
    deducted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assembly = relationship("Assembly", back_populates="material_requirements")

    __table_args__ = (
        Index("ix_amr_assembly", "assembly_id"),
    )
