"""
Drawing Service — v3 Production Drawing Lifecycle
==================================================
Manages the full lifecycle of a shop drawing:
  create → add assemblies/components → release → track instances through stages
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from ..models_v3 import (
    Drawing, Assembly, Component, ComponentInstance,
    StageTransition, MaterialReservation,
    DrawingStatus, ComponentStage, ComponentStageStatus,
    ReservationStatus, DEFAULT_STAGES, StageConfig,
)
from ..models import Customer
from ..models_v2 import MaterialMaster, StockLot


class DrawingService:
    """Service for drawing-based production management (v3)."""

    # -------------------------------------------------------------------------
    # CREATE DRAWING
    # -------------------------------------------------------------------------

    @staticmethod
    def create_drawing(
        db: Session,
        drawing_number: str,
        title: Optional[str],
        customer_id: int,
        project_ref: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Drawing:
        """Create a new drawing in DRAFT status with revision A."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        drawing = Drawing(
            drawing_number=drawing_number,
            title=title,
            customer_id=customer_id,
            project_ref=project_ref,
            notes=notes,
            status=DrawingStatus.DRAFT,
            revision="A",
            total_weight_kg=Decimal("0"),
            completed_weight_kg=Decimal("0"),
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(drawing)
        db.flush()
        return drawing

    # -------------------------------------------------------------------------
    # ADD ASSEMBLY
    # -------------------------------------------------------------------------

    @staticmethod
    def add_assembly(
        db: Session,
        drawing_id: int,
        mark_number: str,
        description: Optional[str] = None,
        quantity_required: int = 1,
        notes: Optional[str] = None,
    ) -> Assembly:
        """Add an assembly (main mark) to a drawing in DRAFT or DETAILED status."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            raise ValueError(f"Drawing {drawing_id} not found")
        if drawing.status not in (DrawingStatus.DRAFT, DrawingStatus.DETAILED):
            raise ValueError(
                f"Cannot add assembly to drawing with status '{drawing.status}'. "
                "Drawing must be DRAFT or DETAILED."
            )

        assembly = Assembly(
            drawing_id=drawing_id,
            mark_number=mark_number,
            description=description,
            quantity_required=quantity_required,
            quantity_complete=0,
            total_weight_kg=Decimal("0"),
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(assembly)
        db.flush()

        DrawingService._recalculate_weights(db, drawing_id)
        return assembly

    # -------------------------------------------------------------------------
    # ADD COMPONENT
    # -------------------------------------------------------------------------

    @staticmethod
    def add_component(
        db: Session,
        assembly_id: int,
        piece_mark: str,
        profile_section: str,
        grade: Optional[str],
        length_mm: Optional[float],
        width_mm: Optional[float],
        thickness_mm: Optional[float],
        quantity_per_assembly: int,
        weight_each_kg: float,
        material_id: Optional[int] = None,
        inventory_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Component:
        """Add a component (piece mark) to an assembly."""
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly {assembly_id} not found")
        drawing = db.query(Drawing).filter(Drawing.id == assembly.drawing_id).first()
        if drawing and drawing.status not in (DrawingStatus.DRAFT, DrawingStatus.DETAILED):
            raise ValueError(
                f"Cannot add component to drawing with status '{drawing.status.value}'. "
                "Drawing must be DRAFT or DETAILED."
            )

        component = Component(
            assembly_id=assembly_id,
            piece_mark=piece_mark,
            profile_section=profile_section,
            grade=grade,
            length_mm=Decimal(str(length_mm)) if length_mm is not None else None,
            width_mm=Decimal(str(width_mm)) if width_mm is not None else None,
            thickness_mm=Decimal(str(thickness_mm)) if thickness_mm is not None else None,
            quantity_per_assembly=quantity_per_assembly,
            weight_each_kg=Decimal(str(weight_each_kg)),
            material_id=material_id,
            inventory_id=inventory_id,
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(component)
        db.flush()

        DrawingService._recalculate_weights(db, assembly.drawing_id)
        return component

    # -------------------------------------------------------------------------
    # RELEASE DRAWING
    # -------------------------------------------------------------------------

    @staticmethod
    def release_drawing(
        db: Session,
        drawing_id: int,
        released_by: int,
    ) -> Drawing:
        """Release a drawing: validate BOM, set status, create all ComponentInstances."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            raise ValueError(f"Drawing {drawing_id} not found")
        if drawing.status not in (DrawingStatus.DRAFT, DrawingStatus.DETAILED, DrawingStatus.CHECKED):
            raise ValueError(
                f"Drawing is already in status '{drawing.status.value}' and cannot be re-released"
            )

        assemblies = drawing.assemblies
        if not assemblies:
            raise ValueError("Cannot release drawing with no assemblies")

        for asm in assemblies:
            if not asm.components:
                raise ValueError(
                    f"Assembly '{asm.mark_number}' has no components. "
                    "All assemblies must have at least one component before release."
                )

        drawing.status = DrawingStatus.RELEASED
        drawing.released_date = datetime.utcnow()
        drawing.released_by = released_by
        drawing.updated_at = datetime.utcnow()
        db.flush()

        for asm in assemblies:
            for comp in asm.components:
                total_instances = comp.quantity_per_assembly * asm.quantity_required
                for instance_num in range(1, total_instances + 1):
                    instance = ComponentInstance(
                        component_id=comp.id,
                        instance_number=instance_num,
                        current_stage="cutting",
                        stage_status=ComponentStageStatus.PENDING,
                        is_completed=False,
                        is_scrapped=False,
                        material_reserved=False,
                        material_issued=False,
                        material_consumed=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(instance)
                    db.flush()

                    transition = StageTransition(
                        component_instance_id=instance.id,
                        from_stage=None,
                        to_stage="cutting",
                        from_status=None,
                        to_status=ComponentStageStatus.PENDING,
                        transitioned_at=datetime.utcnow(),
                        performed_by=released_by,
                        remarks="Drawing released — instance created",
                    )
                    db.add(transition)

        db.flush()
        return drawing

    # -------------------------------------------------------------------------
    # GET DRAWING DETAIL
    # -------------------------------------------------------------------------

    @staticmethod
    def get_drawing_detail(db: Session, drawing_id: int) -> dict:
        """Return drawing with full BOM and instance stage summary."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            raise ValueError(f"Drawing {drawing_id} not found")

        total_instances = 0
        completed_instances = 0
        stage_breakdown: dict[str, int] = {}
        assemblies_data = []

        for asm in drawing.assemblies:
            components_data = []
            for comp in asm.components:
                instances_data = []
                for inst in comp.instances:
                    total_instances += 1
                    if inst.is_completed:
                        completed_instances += 1
                    stage_breakdown[inst.current_stage] = (
                        stage_breakdown.get(inst.current_stage, 0) + 1
                    )
                    instances_data.append({
                        "id": inst.id,
                        "instance_number": inst.instance_number,
                        "current_stage": inst.current_stage,
                        "stage_status": inst.stage_status,
                        "is_completed": inst.is_completed,
                        "is_scrapped": inst.is_scrapped,
                    })
                components_data.append({
                    "id": comp.id,
                    "piece_mark": comp.piece_mark,
                    "profile_section": comp.profile_section,
                    "grade": comp.grade,
                    "weight_each_kg": float(comp.weight_each_kg),
                    "quantity_per_assembly": comp.quantity_per_assembly,
                    "instances": instances_data,
                })
            assemblies_data.append({
                "id": asm.id,
                "mark_number": asm.mark_number,
                "description": asm.description,
                "quantity_required": asm.quantity_required,
                "quantity_complete": asm.quantity_complete,
                "total_weight_kg": float(asm.total_weight_kg or 0),
                "components": components_data,
            })

        return {
            "id": drawing.id,
            "drawing_number": drawing.drawing_number,
            "revision": drawing.revision,
            "title": drawing.title,
            "customer_id": drawing.customer_id,
            "project_ref": drawing.project_ref,
            "status": drawing.status,
            "total_weight_kg": float(drawing.total_weight_kg or 0),
            "completed_weight_kg": float(drawing.completed_weight_kg or 0),
            "released_date": drawing.released_date,
            "assemblies": assemblies_data,
            "total_instances": total_instances,
            "completed_instances": completed_instances,
            "stage_breakdown": stage_breakdown,
        }

    # -------------------------------------------------------------------------
    # LIST DRAWINGS
    # -------------------------------------------------------------------------

    @staticmethod
    def list_drawings(
        db: Session,
        customer_id: Optional[int] = None,
        status: Optional[DrawingStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Drawing]:
        """List drawings with optional filters, newest first."""
        query = db.query(Drawing).options(
            selectinload(Drawing.customer),
            selectinload(Drawing.assemblies)
            .selectinload(Assembly.components)
            .selectinload(Component.instances),
        )
        if customer_id is not None:
            query = query.filter(Drawing.customer_id == customer_id)
        if status is not None:
            query = query.filter(Drawing.status == status)
        return (
            query.order_by(Drawing.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # -------------------------------------------------------------------------
    # GET STAGE PIPELINE
    # -------------------------------------------------------------------------

    @staticmethod
    def get_stage_pipeline(
        db: Session,
        customer_id: Optional[int] = None,
    ) -> List[dict]:
        """Return ordered stage config for a customer, falling back to defaults."""
        query = db.query(StageConfig).filter(StageConfig.customer_id == customer_id)
        configs = query.order_by(StageConfig.sequence.asc()).all()

        if configs:
            return [
                {
                    "stage_name": cfg.stage_name,
                    "sequence": cfg.sequence,
                    "is_mandatory": cfg.is_mandatory,
                    "requires_qa_hold": cfg.requires_qa_hold,
                    "auto_deduct_material": cfg.auto_deduct_material,
                }
                for cfg in configs
            ]

        return sorted(DEFAULT_STAGES, key=lambda s: s["sequence"])

    # -------------------------------------------------------------------------
    # RECALCULATE WEIGHTS (private)
    # -------------------------------------------------------------------------

    @staticmethod
    def _recalculate_weights(db: Session, drawing_id: int) -> None:
        """Recalculate assembly and drawing total weights from component data."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            return

        drawing_total = Decimal("0")
        drawing_completed = Decimal("0")

        for asm in drawing.assemblies:
            asm_total = Decimal("0")
            for comp in asm.components:
                total_qty = comp.quantity_per_assembly * asm.quantity_required
                asm_total += Decimal(str(comp.weight_each_kg)) * total_qty

            asm.total_weight_kg = asm_total
            asm.updated_at = datetime.utcnow()
            drawing_total += asm_total

            # Sum completed instance weights
            for comp in asm.components:
                completed_count = sum(
                    1 for inst in comp.instances if inst.is_completed
                )
                drawing_completed += (
                    Decimal(str(comp.weight_each_kg)) * completed_count
                )

        drawing.total_weight_kg = drawing_total
        drawing.completed_weight_kg = drawing_completed
        drawing.updated_at = datetime.utcnow()
        db.flush()

    # -------------------------------------------------------------------------
    # UPDATE DRAWING STATUS
    # -------------------------------------------------------------------------

    @staticmethod
    def update_drawing_status(db: Session, drawing_id: int) -> None:
        """Sync drawing status based on aggregate instance states."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            return

        if drawing.status in (DrawingStatus.DRAFT, DrawingStatus.RELEASED):
            # Only transition from RELEASED onward
            if drawing.status == DrawingStatus.DRAFT:
                return

        all_instances: List[ComponentInstance] = []
        for asm in drawing.assemblies:
            for comp in asm.components:
                all_instances.extend(comp.instances)

        if not all_instances:
            return

        all_complete = all(inst.is_completed for inst in all_instances)
        any_in_progress = any(
            inst.stage_status == ComponentStageStatus.IN_PROGRESS
            for inst in all_instances
        )

        if all_complete:
            drawing.status = DrawingStatus.COMPLETE
        elif any_in_progress:
            drawing.status = DrawingStatus.IN_PROGRESS

        drawing.updated_at = datetime.utcnow()
        DrawingService._recalculate_weights(db, drawing_id)
        db.flush()

    # -------------------------------------------------------------------------
    # MATERIAL USAGE PER DRAWING
    # -------------------------------------------------------------------------

    @staticmethod
    def get_material_usage(db: Session, drawing_id: int) -> dict:
        """Return complete material usage report for a drawing."""
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            raise ValueError(f"Drawing {drawing_id} not found")

        from ..models_v2 import StockLot, MaterialMaster
        from ..models import Inventory

        total_bom_kg = Decimal("0")
        total_consumed_kg = Decimal("0")
        total_reserved_kg = Decimal("0")

        assembly_usages = []
        for asm in drawing.assemblies:
            comp_usages = []
            asm_required = Decimal("0")
            asm_consumed = Decimal("0")

            for comp in asm.components:
                total_qty = comp.quantity_per_assembly * asm.quantity_required
                required_kg = comp.weight_each_kg * total_qty
                asm_required += required_kg
                total_bom_kg += required_kg

                consumed_count = 0
                pending_count = 0
                comp_consumed_kg = Decimal("0")
                comp_reserved_kg = Decimal("0")
                lot_numbers = set()
                heat_numbers = set()

                for inst in comp.instances:
                    if inst.material_consumed:
                        consumed_count += 1
                        comp_consumed_kg += comp.weight_each_kg
                    else:
                        pending_count += 1

                    if inst.material_reserved:
                        comp_reserved_kg += comp.weight_each_kg

                    if inst.heat_number:
                        heat_numbers.add(inst.heat_number)

                    # Get lot numbers from reservations
                    for res in inst.reservations:
                        if res.stock_lot_id:
                            lot = db.query(StockLot).filter(
                                StockLot.id == res.stock_lot_id
                            ).first()
                            if lot:
                                lot_numbers.add(lot.lot_number)
                                if lot.heat_number:
                                    heat_numbers.add(lot.heat_number)

                asm_consumed += comp_consumed_kg
                total_consumed_kg += comp_consumed_kg
                total_reserved_kg += comp_reserved_kg

                # Resolve material name
                mat_name = None
                if comp.material_id:
                    mat = db.query(MaterialMaster).filter(
                        MaterialMaster.id == comp.material_id
                    ).first()
                    if mat:
                        mat_name = f"{mat.name} ({mat.code})"
                elif comp.inventory_id:
                    inv = db.query(Inventory).filter(
                        Inventory.id == comp.inventory_id
                    ).first()
                    if inv:
                        mat_name = f"{inv.name} ({inv.code})" if inv.code else inv.name

                comp_usages.append({
                    "piece_mark": comp.piece_mark,
                    "profile_section": comp.profile_section,
                    "grade": comp.grade,
                    "weight_each_kg": float(comp.weight_each_kg),
                    "total_instances": len(comp.instances),
                    "instances_consumed": consumed_count,
                    "instances_pending": pending_count,
                    "total_required_kg": float(required_kg),
                    "total_consumed_kg": float(comp_consumed_kg),
                    "total_reserved_kg": float(comp_reserved_kg),
                    "material_name": mat_name,
                    "stock_lot_numbers": sorted(lot_numbers),
                    "heat_numbers": sorted(heat_numbers),
                })

            assembly_usages.append({
                "mark_number": asm.mark_number,
                "description": asm.description,
                "quantity_required": asm.quantity_required,
                "quantity_complete": asm.quantity_complete,
                "components": comp_usages,
                "subtotal_required_kg": float(asm_required),
                "subtotal_consumed_kg": float(asm_consumed),
            })

        total_pending = total_bom_kg - total_reserved_kg
        consumption_pct = (
            float(total_consumed_kg / total_bom_kg * 100)
            if total_bom_kg > 0 else 0.0
        )

        customer_name = drawing.customer.name if drawing.customer else None

        return {
            "drawing_id": drawing.id,
            "drawing_number": drawing.drawing_number,
            "revision": drawing.revision,
            "customer_name": customer_name,
            "status": drawing.status.value if hasattr(drawing.status, 'value') else str(drawing.status),
            "assemblies": assembly_usages,
            "total_bom_weight_kg": float(total_bom_kg),
            "total_consumed_kg": float(total_consumed_kg),
            "total_reserved_kg": float(total_reserved_kg),
            "total_pending_kg": float(total_pending),
            "consumption_pct": round(consumption_pct, 1),
        }
