"""
BOMService — Business logic for Bill of Materials operations.

Handles:
  - Assembly CRUD with nested parts
  - Material requirement calculation from parts
  - Weight aggregation
  - CSV/Excel import grouping by assembly_code
"""
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from ..models_bom import (
    Assembly,
    AssemblyPart,
    AssemblyStageTracking,
    AssemblyMaterialRequirement,
)
from .. import models

logger = logging.getLogger(__name__)

STAGES = ["fabrication", "painting", "dispatch"]


class BOMService:
    """Bill of Materials business logic."""

    # ------------------------------------------------------------------
    # Assembly CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_assembly(
        db: Session,
        customer_id: int,
        assembly_code: str,
        assembly_name: str,
        drawing_number: Optional[str] = None,
        revision: Optional[str] = None,
        ordered_qty: int = 1,
        lot_number: Optional[str] = None,
        notes: Optional[str] = None,
        parts: Optional[list] = None,
    ) -> Assembly:
        """Create an assembly with optional inline parts."""
        # Verify customer exists
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found")

        assembly = Assembly(
            customer_id=customer_id,
            assembly_code=assembly_code,
            assembly_name=assembly_name,
            drawing_number=drawing_number,
            revision=revision,
            ordered_qty=ordered_qty,
            lot_number=lot_number,
            notes=notes,
        )
        db.add(assembly)
        db.flush()  # Get assembly.id

        # Create initial stage tracking for all stages
        total_pieces = 0
        if parts:
            for part_data in parts:
                part = BOMService._create_part_from_dict(db, assembly.id, part_data)
                total_pieces += part.total_qty

        for stage in STAGES:
            st = AssemblyStageTracking(
                assembly_id=assembly.id,
                stage=stage,
                status="pending",
                total_pieces=total_pieces,
                completed_pieces=0,
            )
            db.add(st)

        # Calculate estimated weight
        assembly.estimated_weight_kg = BOMService._calculate_assembly_weight(db, assembly.id)
        db.add(assembly)
        db.commit()
        db.refresh(assembly)
        return assembly

    @staticmethod
    def get_assembly(db: Session, assembly_id: int) -> Optional[Assembly]:
        """Get assembly with all relations loaded."""
        return db.query(Assembly).filter(Assembly.id == assembly_id).first()

    @staticmethod
    def list_assemblies(
        db: Session,
        customer_id: Optional[int] = None,
        search: Optional[str] = None,
        lot_number: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list:
        """List assemblies with optional filters."""
        query = db.query(Assembly)

        if customer_id:
            query = query.filter(Assembly.customer_id == customer_id)
        if lot_number:
            query = query.filter(Assembly.lot_number == lot_number)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Assembly.assembly_code.ilike(term),
                    Assembly.assembly_name.ilike(term),
                    Assembly.drawing_number.ilike(term),
                )
            )

        return query.order_by(Assembly.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_assembly(db: Session, assembly_id: int, update_data: dict) -> Assembly:
        """Update assembly metadata."""
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly ID {assembly_id} not found")

        for field, value in update_data.items():
            if value is not None and hasattr(assembly, field):
                setattr(assembly, field, value)

        db.add(assembly)
        db.commit()
        db.refresh(assembly)
        return assembly

    # ------------------------------------------------------------------
    # Part CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def add_part(db: Session, assembly_id: int, part_data: dict) -> AssemblyPart:
        """Add a part to an assembly."""
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly ID {assembly_id} not found")

        part = BOMService._create_part_from_dict(db, assembly_id, part_data)

        # Update assembly weight and stage piece counts
        BOMService._recalculate_assembly(db, assembly_id)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def update_part(db: Session, part_id: int, update_data: dict) -> AssemblyPart:
        """Update a part."""
        part = db.query(AssemblyPart).filter(AssemblyPart.id == part_id).first()
        if not part:
            raise ValueError(f"Part ID {part_id} not found")

        for field, value in update_data.items():
            if value is not None and hasattr(part, field):
                setattr(part, field, value)

        # Recalculate total_weight_kg
        if part.weight_per_unit_kg and part.total_qty:
            part.total_weight_kg = Decimal(str(part.weight_per_unit_kg)) * part.total_qty

        db.add(part)
        BOMService._recalculate_assembly(db, part.assembly_id)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def delete_part(db: Session, part_id: int) -> None:
        """Delete a part from an assembly."""
        part = db.query(AssemblyPart).filter(AssemblyPart.id == part_id).first()
        if not part:
            raise ValueError(f"Part ID {part_id} not found")

        assembly_id = part.assembly_id
        db.delete(part)
        db.flush()  # Flush the delete so recalculation sees updated data
        BOMService._recalculate_assembly(db, assembly_id)
        db.commit()

    # ------------------------------------------------------------------
    # Material Requirements
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_material_requirements(db: Session, assembly_id: int) -> list:
        """
        Auto-calculate material requirements from parts.
        Groups by section/material to create aggregated requirements.
        """
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly ID {assembly_id} not found")

        # Clear existing auto-calculated requirements
        db.query(AssemblyMaterialRequirement).filter(
            AssemblyMaterialRequirement.assembly_id == assembly_id,
            AssemblyMaterialRequirement.deducted == False,
        ).delete()

        parts = db.query(AssemblyPart).filter(AssemblyPart.assembly_id == assembly_id).all()

        # Group by section (material type)
        material_groups = {}
        for part in parts:
            key = part.section or part.part_name
            if key not in material_groups:
                material_groups[key] = {
                    "total_weight": Decimal("0"),
                    "inventory_id": part.inventory_id,
                    "material_master_id": part.material_master_id,
                    "parts": [],
                }

            weight = Decimal(str(part.total_weight_kg or 0))
            material_groups[key]["total_weight"] += weight
            material_groups[key]["parts"].append(part)

        # Create requirement records
        requirements = []
        for material_name, group in material_groups.items():
            if group["total_weight"] <= 0:
                continue

            # Try to auto-match inventory if not explicitly linked
            inv_id = group["inventory_id"]
            if not inv_id:
                inv = db.query(models.Inventory).filter(
                    or_(
                        models.Inventory.name.ilike(f"%{material_name}%"),
                        models.Inventory.section.ilike(f"%{material_name}%"),
                    )
                ).first()
                if inv:
                    inv_id = inv.id

            req = AssemblyMaterialRequirement(
                assembly_id=assembly_id,
                inventory_id=inv_id,
                material_master_id=group["material_master_id"],
                material_name=material_name,
                required_qty_kg=group["total_weight"],
            )
            db.add(req)
            requirements.append(req)

        db.commit()
        return requirements

    @staticmethod
    def get_requirements(db: Session, assembly_id: int) -> list:
        """Get material requirements for an assembly."""
        return (
            db.query(AssemblyMaterialRequirement)
            .filter(AssemblyMaterialRequirement.assembly_id == assembly_id)
            .all()
        )

    # ------------------------------------------------------------------
    # CSV/Excel Import
    # ------------------------------------------------------------------

    @staticmethod
    def import_from_rows(
        db: Session,
        customer_id: int,
        rows: list,
    ) -> dict:
        """
        Import assemblies + parts from parsed rows (CSV or Excel).

        Rows should be dicts with keys like:
            assembly_code, assembly_name, drawing_number, lot_number,
            mark_number, part_name, section, length_mm, width_mm,
            thickness_mm, total_qty/qty, weight_per_unit_kg, material_grade

        Groups by assembly_code to create Assembly + AssemblyPart records.
        """
        result = {"assemblies_created": 0, "parts_created": 0, "errors": [], "warnings": []}

        # Group rows by assembly_code
        assembly_groups = {}
        for i, row in enumerate(rows):
            code = str(row.get("assembly_code", "")).strip()
            if not code:
                result["errors"].append(f"Row {i + 1}: missing assembly_code")
                continue
            if code not in assembly_groups:
                assembly_groups[code] = {"meta": row, "parts": []}
            assembly_groups[code]["parts"].append(row)

        for code, group in assembly_groups.items():
            meta = group["meta"]
            try:
                with db.begin_nested():
                    # Check if assembly already exists for this customer + code + lot
                    lot = str(meta.get("lot_number", "")).strip() or None
                    existing_query = db.query(Assembly).filter(
                        Assembly.customer_id == customer_id,
                        Assembly.assembly_code == code,
                    )
                    if lot:
                        existing_query = existing_query.filter(Assembly.lot_number == lot)
                    else:
                        existing_query = existing_query.filter(Assembly.lot_number.is_(None))
                    existing = existing_query.first()

                    if existing:
                        assembly = existing
                        result["warnings"].append(f"Assembly '{code}' already exists, adding parts to it")
                    else:
                        assembly = Assembly(
                            customer_id=customer_id,
                            assembly_code=code,
                            assembly_name=str(meta.get("assembly_name", code)).strip(),
                            drawing_number=str(meta.get("drawing_number", "")).strip() or None,
                            lot_number=lot,
                            ordered_qty=int(meta.get("ordered_qty", 1) or 1),
                            notes=str(meta.get("notes", "")).strip() or None,
                        )
                        db.add(assembly)
                        db.flush()
                        result["assemblies_created"] += 1

                    # Add parts
                    for row in group["parts"]:
                        mark = str(row.get("mark_number", "")).strip()
                        if not mark:
                            continue  # Skip rows without mark numbers (assembly-level only)

                        qty = int(row.get("total_qty", row.get("qty", 1)) or 1)
                        wpk = float(row.get("weight_per_unit_kg", 0) or 0)

                        part = AssemblyPart(
                            assembly_id=assembly.id,
                            mark_number=mark,
                            part_name=str(row.get("part_name", mark)).strip(),
                            drawing_number=str(row.get("drawing_number", "")).strip() or None,
                            section=str(row.get("section", "")).strip() or None,
                            material_grade=str(row.get("material_grade", "")).strip() or None,
                            length_mm=Decimal(str(row.get("length_mm", 0) or 0)) or None,
                            width_mm=Decimal(str(row.get("width_mm", 0) or 0)) or None,
                            thickness_mm=Decimal(str(row.get("thickness_mm", 0) or 0)) or None,
                            total_qty=qty,
                            weight_per_unit_kg=Decimal(str(wpk)) if wpk else None,
                            total_weight_kg=Decimal(str(wpk * qty)) if wpk else None,
                        )
                        db.add(part)
                        result["parts_created"] += 1

                    # Create stage tracking if new assembly
                    if not existing:
                        total_pieces = sum(
                            int(r.get("total_qty", r.get("qty", 1)) or 1)
                            for r in group["parts"]
                            if r.get("mark_number")
                        )
                        for stage in STAGES:
                            st = AssemblyStageTracking(
                                assembly_id=assembly.id,
                                stage=stage,
                                total_pieces=total_pieces,
                            )
                            db.add(st)

                    # Recalculate weight
                    BOMService._recalculate_assembly(db, assembly.id)

            except Exception as e:
                result["errors"].append(f"Assembly '{code}': {str(e)}")
                logger.error("Failed to import assembly %s: %s", code, e)

        db.commit()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_part_from_dict(db: Session, assembly_id: int, data: dict) -> AssemblyPart:
        """Create an AssemblyPart from a dict of field values."""
        mark = data.get("mark_number")
        if not mark:
            raise ValueError("mark_number is required for assembly parts")

        qty = int(data.get("total_qty", 1) or 1)
        wpk = data.get("weight_per_unit_kg")
        wpk_decimal = Decimal(str(wpk)) if wpk else None
        total_weight = (wpk_decimal * qty) if wpk_decimal else None

        part = AssemblyPart(
            assembly_id=assembly_id,
            mark_number=mark,
            part_name=data.get("part_name", mark),
            drawing_number=data.get("drawing_number"),
            section=data.get("section"),
            material_grade=data.get("material_grade"),
            length_mm=Decimal(str(data["length_mm"])) if data.get("length_mm") else None,
            width_mm=Decimal(str(data["width_mm"])) if data.get("width_mm") else None,
            thickness_mm=Decimal(str(data["thickness_mm"])) if data.get("thickness_mm") else None,
            total_qty=qty,
            weight_per_unit_kg=wpk_decimal,
            total_weight_kg=total_weight,
            material_master_id=data.get("material_master_id"),
            inventory_id=data.get("inventory_id"),
        )
        db.add(part)
        db.flush()
        return part

    @staticmethod
    def _calculate_assembly_weight(db: Session, assembly_id: int) -> Decimal:
        """Sum total_weight_kg across all parts."""
        result = (
            db.query(func.sum(AssemblyPart.total_weight_kg))
            .filter(AssemblyPart.assembly_id == assembly_id)
            .scalar()
        )
        return result or Decimal("0")

    @staticmethod
    def _recalculate_assembly(db: Session, assembly_id: int):
        """Recalculate assembly weight and stage piece counts."""
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            return

        # Recalculate weight
        assembly.estimated_weight_kg = BOMService._calculate_assembly_weight(db, assembly_id)
        db.add(assembly)

        # Recalculate total pieces for each stage
        total_pieces = (
            db.query(func.sum(AssemblyPart.total_qty))
            .filter(AssemblyPart.assembly_id == assembly_id)
            .scalar()
        ) or 0

        for st in assembly.stage_tracking:
            st.total_pieces = total_pieces
            db.add(st)
