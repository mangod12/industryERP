"""
Component Tracking Service — KBSteel ERP v3
============================================
Manages stage-by-stage progression of physical component instances through
the fabrication pipeline. Provides:
- Stage advancement with validation and audit trail
- Automatic material deduction on configurable stages
- Drawing / assembly completion rollup
- Kanban view grouped by stage

Pattern: static methods on a class, db: Session parameter (matches inventory_service.py).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models_v3 import (
    ComponentInstance,
    Component,
    Assembly,
    Drawing,
    StageTransition,
    MaterialReservation,
    StageConfig,
    ComponentStageStatus,
    ReservationStatus,
    DEFAULT_STAGES,
    DrawingStatus,
)
from ..models_v2 import StockLot, StockMovement, MovementType
from ..models import Inventory


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_next_sequence_number(db: Session) -> str:
    """Simple movement number generator (reuses existing pattern)."""
    from .inventory_service import get_next_sequence
    return get_next_sequence(db, "movement", "MOV")


# =============================================================================
# COMPONENT TRACKING SERVICE
# =============================================================================

class ComponentTrackingService:
    """Stage-based production tracking for v3 component instances."""

    # -------------------------------------------------------------------------
    # Public: stage control
    # -------------------------------------------------------------------------

    @staticmethod
    def advance_stage(
        db: Session,
        instance_id: int,
        user_id: int,
        target_stage: Optional[str] = None,
        remarks: Optional[str] = None,
        station: Optional[str] = None,
    ) -> dict:
        """
        Advance a component instance to the next (or specified) stage.

        Validates ordering, triggers material deduction if the stage is
        configured with auto_deduct_material, creates an immutable
        StageTransition record, and rolls up drawing progress.

        Returns {instance_id, from_stage, to_stage, deduction_result}.
        """
        instance = (
            db.query(ComponentInstance)
            .filter(ComponentInstance.id == instance_id)
            .with_for_update()
            .first()
        )
        if not instance:
            raise ValueError(f"ComponentInstance {instance_id} not found")
        if instance.is_scrapped:
            raise ValueError(f"Instance {instance_id} is scrapped — cannot advance stage")

        pipeline, from_stage, resolved_target = (
            ComponentTrackingService._resolve_advance_target(db, instance, target_stage)
        )

        deduction_result = ComponentTrackingService._maybe_deduct(
            db, instance, pipeline, from_stage, user_id
        )

        ComponentTrackingService._apply_stage_transition(
            db, instance, from_stage, resolved_target,
            user_id, station, remarks, deduction_result
        )

        db.flush()
        ComponentTrackingService._update_drawing_progress(db, instance)

        return {
            "instance_id": instance.id,
            "from_stage": from_stage,
            "to_stage": resolved_target,
            "deduction_result": deduction_result,
        }

    @staticmethod
    def _resolve_advance_target(
        db: Session,
        instance: ComponentInstance,
        target_stage: Optional[str],
    ) -> tuple:
        """Return (pipeline, from_stage, resolved_target) for advance_stage."""
        component = db.query(Component).filter(Component.id == instance.component_id).first()
        assembly = db.query(Assembly).filter(Assembly.id == component.assembly_id).first()
        customer_id = (
            db.query(Drawing.customer_id)
            .filter(Drawing.id == assembly.drawing_id)
            .scalar()
        )
        pipeline = ComponentTrackingService._get_stage_pipeline(db, customer_id)
        from_stage = instance.current_stage
        resolved = (
            target_stage
            or ComponentTrackingService._get_next_stage(pipeline, from_stage)
        )
        if resolved is None:
            raise ValueError(f"Instance {instance.id} is already at the last stage")
        ComponentTrackingService._validate_stage_order(pipeline, from_stage, resolved)
        return pipeline, from_stage, resolved

    @staticmethod
    def _maybe_deduct(
        db: Session,
        instance: ComponentInstance,
        pipeline: list,
        from_stage: str,
        user_id: int,
    ) -> Optional[dict]:
        """Trigger material deduction if the departing stage requires it."""
        stage_cfg = next((s for s in pipeline if s["stage_name"] == from_stage), {})
        if stage_cfg.get("auto_deduct_material") and not instance.material_consumed:
            return ComponentTrackingService._deduct_material_for_component(
                db, instance, user_id
            )
        return None

    @staticmethod
    def _apply_stage_transition(
        db: Session,
        instance: ComponentInstance,
        from_stage: str,
        to_stage: str,
        user_id: int,
        station: Optional[str],
        remarks: Optional[str],
        deduction_result: Optional[dict],
    ) -> None:
        """Write StageTransition record and mutate the instance fields."""
        prev_status = instance.stage_status.value if instance.stage_status else None
        new_status = (
            ComponentStageStatus.COMPLETED
            if to_stage == "completed"
            else ComponentStageStatus.IN_PROGRESS
        )
        transition = StageTransition(
            component_instance_id=instance.id,
            from_stage=from_stage,
            to_stage=to_stage,
            from_status=prev_status,
            to_status=new_status.value,
            transitioned_at=datetime.utcnow(),
            performed_by=user_id,
            station=station,
            remarks=remarks,
            deduction_result=deduction_result,
        )
        db.add(transition)
        instance.current_stage = to_stage
        instance.stage_status = new_status
        instance.stage_updated_at = datetime.utcnow()
        instance.stage_updated_by = user_id
        if to_stage == "completed":
            instance.is_completed = True
            instance.completed_at = datetime.utcnow()

    @staticmethod
    def batch_advance(
        db: Session,
        instance_ids: list,
        user_id: int,
        target_stage: Optional[str] = None,
        remarks: Optional[str] = None,
        station: Optional[str] = None,
    ) -> list:
        """
        Advance multiple instances in a single call.

        Each advance is attempted independently so that one failure does not
        block others. Failed instances are included in the result with an
        'error' key instead of stage data.
        """
        results = []
        for iid in instance_ids:
            savepoint = db.begin_nested()
            try:
                result = ComponentTrackingService.advance_stage(
                    db, iid, user_id, target_stage, remarks, station
                )
                savepoint.commit()
                results.append(result)
            except (ValueError, Exception) as exc:
                savepoint.rollback()
                results.append({"instance_id": iid, "error": str(exc)})
        return results

    @staticmethod
    def start_stage(db: Session, instance_id: int, user_id: int) -> dict:
        """
        Mark the current stage as IN_PROGRESS without changing the stage name.

        Useful when a worker picks up a piece that is PENDING or ON_HOLD.
        """
        instance = (
            db.query(ComponentInstance)
            .filter(ComponentInstance.id == instance_id)
            .with_for_update()
            .first()
        )
        if not instance:
            raise ValueError(f"ComponentInstance {instance_id} not found")

        prev_status = instance.stage_status.value if instance.stage_status else None
        new_status = ComponentStageStatus.IN_PROGRESS

        transition = StageTransition(
            component_instance_id=instance.id,
            from_stage=instance.current_stage,
            to_stage=instance.current_stage,
            from_status=prev_status,
            to_status=new_status.value,
            transitioned_at=datetime.utcnow(),
            performed_by=user_id,
            remarks="Stage started",
        )
        db.add(transition)

        instance.stage_status = new_status
        instance.stage_updated_at = datetime.utcnow()
        instance.stage_updated_by = user_id
        db.flush()

        return {
            "instance_id": instance.id,
            "current_stage": instance.current_stage,
            "stage_status": new_status.value,
        }

    @staticmethod
    def hold_stage(
        db: Session, instance_id: int, user_id: int, reason: str
    ) -> dict:
        """
        Place a component instance on hold at its current stage.

        Creates an audit transition with the hold reason.
        """
        if not reason or not reason.strip():
            raise ValueError("A hold reason must be provided")

        instance = (
            db.query(ComponentInstance)
            .filter(ComponentInstance.id == instance_id)
            .with_for_update()
            .first()
        )
        if not instance:
            raise ValueError(f"ComponentInstance {instance_id} not found")

        prev_status = instance.stage_status.value if instance.stage_status else None
        new_status = ComponentStageStatus.ON_HOLD

        transition = StageTransition(
            component_instance_id=instance.id,
            from_stage=instance.current_stage,
            to_stage=instance.current_stage,
            from_status=prev_status,
            to_status=new_status.value,
            transitioned_at=datetime.utcnow(),
            performed_by=user_id,
            remarks=reason,
        )
        db.add(transition)

        instance.stage_status = new_status
        instance.stage_updated_at = datetime.utcnow()
        instance.stage_updated_by = user_id
        db.flush()

        return {
            "instance_id": instance.id,
            "current_stage": instance.current_stage,
            "stage_status": new_status.value,
            "hold_reason": reason,
        }

    @staticmethod
    def scrap_instance(
        db: Session, instance_id: int, user_id: int, reason: str
    ) -> dict:
        """Mark a component as scrapped; logs waste movement if material consumed."""
        if not reason or not reason.strip():
            raise ValueError("A scrap reason must be provided")
        instance = (
            db.query(ComponentInstance)
            .filter(ComponentInstance.id == instance_id)
            .with_for_update()
            .first()
        )
        if not instance:
            raise ValueError(f"ComponentInstance {instance_id} not found")
        if instance.is_scrapped:
            raise ValueError(f"Instance {instance_id} is already scrapped")

        ComponentTrackingService._record_scrap_waste(db, instance, user_id, reason)

        prev_status = instance.stage_status.value if instance.stage_status else None
        transition = StageTransition(
            component_instance_id=instance.id,
            from_stage=instance.current_stage,
            to_stage="scrapped",
            from_status=prev_status,
            to_status="scrapped",
            transitioned_at=datetime.utcnow(),
            performed_by=user_id,
            remarks=reason,
        )
        db.add(transition)
        instance.is_scrapped = True
        instance.scrap_reason = reason
        instance.stage_updated_at = datetime.utcnow()
        instance.stage_updated_by = user_id
        db.flush()
        return {
            "instance_id": instance.id,
            "is_scrapped": True,
            "scrap_reason": reason,
            "stage_at_scrap": instance.current_stage,
        }

    @staticmethod
    def _record_scrap_waste(
        db: Session,
        instance: ComponentInstance,
        user_id: int,
        reason: str,
    ) -> None:
        """Log an OUTWARD_SCRAP movement when scrapping an already-consumed instance."""
        if not (instance.material_consumed and instance.stock_lot_id):
            return
        component = db.query(Component).filter(
            Component.id == instance.component_id
        ).first()
        weight_kg = Decimal(str(component.weight_each_kg)) if component else Decimal("0")
        if weight_kg <= 0:
            return
        lot = db.query(StockLot).filter(StockLot.id == instance.stock_lot_id).first()
        if not lot:
            return
        scrap_movement = StockMovement(
            movement_number=_get_next_sequence_number(db),
            stock_lot_id=lot.id,
            movement_type=MovementType.OUTWARD_SCRAP,
            weight_change_kg=Decimal("0"),  # already consumed; zero net change
            weight_before_kg=lot.current_weight_kg,
            weight_after_kg=lot.current_weight_kg,
            reason=f"Scrap waste — instance {instance.id}: {reason}",
            created_by=user_id,
            movement_date=datetime.utcnow(),
        )
        db.add(scrap_movement)

    # -------------------------------------------------------------------------
    # Public: read operations
    # -------------------------------------------------------------------------

    @staticmethod
    def get_kanban(
        db: Session,
        drawing_id: Optional[int] = None,
        customer_id: Optional[int] = None,
    ) -> dict:
        """
        Return all active (non-scrapped, non-completed) instances grouped by
        current_stage.

        Each card contains: instance_id, piece_mark, drawing_number,
        assembly_mark, and current stage_status.
        """
        rows = ComponentTrackingService._query_kanban_rows(db, drawing_id, customer_id)
        kanban: dict = {}
        for inst, piece_mark, assembly_mark, drawing_number, _ in rows:
            card = {
                "instance_id": inst.id,
                "piece_mark": piece_mark,
                "drawing_number": drawing_number,
                "assembly_mark": assembly_mark,
                "status": inst.stage_status.value if inst.stage_status else None,
                "stage_updated_at": inst.stage_updated_at,
            }
            kanban.setdefault(inst.current_stage, []).append(card)
        return kanban

    @staticmethod
    def _query_kanban_rows(
        db: Session,
        drawing_id: Optional[int],
        customer_id: Optional[int],
    ) -> list:
        """Execute the kanban base query and apply optional filters."""
        query = (
            db.query(
                ComponentInstance,
                Component.piece_mark,
                Assembly.mark_number,
                Drawing.drawing_number,
                Drawing.customer_id,
            )
            .join(Component, ComponentInstance.component_id == Component.id)
            .join(Assembly, Component.assembly_id == Assembly.id)
            .join(Drawing, Assembly.drawing_id == Drawing.id)
            .filter(
                ComponentInstance.is_scrapped == False,
                ComponentInstance.is_completed == False,
            )
        )
        if drawing_id:
            query = query.filter(Drawing.id == drawing_id)
        if customer_id:
            query = query.filter(Drawing.customer_id == customer_id)
        return query.all()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _deduct_material_for_component(
        db: Session, instance: ComponentInstance, user_id: int
    ) -> dict:
        """
        Consume material for this instance.

        Priority:
        1. v2 path: component.material_id → StockLot (use reservation if exists, else FIFO)
        2. v1 fallback: component.inventory_id → Inventory.used increment

        Returns a result dict with success, material_name, weight_deducted,
        lot_number (v2) or None (v1), and any warnings.
        """
        component = db.query(Component).filter(
            Component.id == instance.component_id
        ).first()
        if not component:
            return {"success": False, "warnings": ["Component not found"]}

        weight_kg = Decimal(str(component.weight_each_kg))
        warnings = []

        # ------------------------------------------------------------------
        # v2 path: material_id present
        # ------------------------------------------------------------------
        if component.material_id:
            return ComponentTrackingService._deduct_v2(
                db, instance, component, weight_kg, user_id, warnings
            )

        # ------------------------------------------------------------------
        # v1 fallback: inventory_id present
        # ------------------------------------------------------------------
        if component.inventory_id:
            return ComponentTrackingService._deduct_v1(
                db, instance, component, weight_kg, warnings
            )

        warnings.append("No material link on component — skipping deduction")
        return {"success": False, "weight_deducted": 0, "warnings": warnings}

    @staticmethod
    def _deduct_v2(
        db: Session,
        instance: ComponentInstance,
        component: Component,
        weight_kg: Decimal,
        user_id: int,
        warnings: list,
    ) -> dict:
        """Consume weight from a v2 StockLot (reservation-first, then FIFO)."""
        from .inventory_service import StockLotService

        reservation, lot_id = ComponentTrackingService._pick_lot_for_deduction(
            db, instance, component, weight_kg, warnings
        )
        if lot_id is None:
            return {"success": False, "weight_deducted": 0, "warnings": warnings}

        movement, lot = StockLotService.consume_from_lot(
            db=db,
            lot_id=lot_id,
            weight_kg=weight_kg,
            user_id=user_id,
            reason=f"Fabrication deduction — instance {instance.id}",
            reference_type="component_instance",
            reference_id=instance.id,
        )

        ComponentTrackingService._finalise_reservation(reservation, weight_kg, movement.id)

        instance.material_consumed = True
        instance.stock_lot_id = lot_id
        instance.heat_number = lot.heat_number

        material_name = (
            lot.material.name if lot.material else f"material_id={component.material_id}"
        )
        return {
            "success": True,
            "material_name": material_name,
            "weight_deducted": float(weight_kg),
            "lot_number": lot.lot_number,
            "warnings": warnings,
        }

    @staticmethod
    def _pick_lot_for_deduction(
        db: Session,
        instance: ComponentInstance,
        component: Component,
        weight_kg: Decimal,
        warnings: list,
    ) -> tuple:
        """
        Return (reservation_or_None, lot_id_or_None) for the deduction.

        Checks an active MaterialReservation first; falls back to FIFO.
        Appends to warnings list in-place when falling back.
        """
        reservation = (
            db.query(MaterialReservation)
            .filter(
                and_(
                    MaterialReservation.component_instance_id == instance.id,
                    MaterialReservation.status.in_(
                        [ReservationStatus.RESERVED, ReservationStatus.ISSUED]
                    ),
                )
            )
            .with_for_update()
            .first()
        )
        if reservation:
            return reservation, reservation.stock_lot_id

        # FIFO fallback
        warnings.append("No reservation found — falling back to FIFO lot selection")
        fifo_lot = (
            db.query(StockLot)
            .filter(
                and_(
                    StockLot.material_id == component.material_id,
                    StockLot.is_active == True,
                    StockLot.is_blocked == False,
                    StockLot.current_weight_kg >= weight_kg,
                )
            )
            .order_by(StockLot.received_date.asc())
            .first()
        )
        if not fifo_lot:
            warnings.append("No eligible lot with sufficient stock")
            return None, None
        return None, fifo_lot.id

    @staticmethod
    def _finalise_reservation(
        reservation: Optional[MaterialReservation],
        weight_kg: Decimal,
        movement_id: int,
    ) -> None:
        """Mark an existing reservation as CONSUMED after deduction."""
        if not reservation:
            return
        reservation.status = ReservationStatus.CONSUMED
        reservation.consumed_weight_kg = weight_kg
        reservation.consumed_at = datetime.utcnow()
        reservation.consume_movement_id = movement_id

    @staticmethod
    def _deduct_v1(
        db: Session,
        instance: ComponentInstance,
        component: Component,
        weight_kg: Decimal,
        warnings: list,
    ) -> dict:
        """Consume weight from v1 Inventory by incrementing the used column."""
        inv = (
            db.query(Inventory)
            .filter(Inventory.id == component.inventory_id)
            .with_for_update()
            .first()
        )
        if not inv:
            return {
                "success": False,
                "weight_deducted": 0,
                "warnings": warnings + [f"Inventory {component.inventory_id} not found"],
            }

        available = inv.total - inv.used
        deduct = float(weight_kg)
        if available < deduct:
            warnings.append(
                f"Inventory shortfall: need {deduct} kg, available {available} kg — "
                "deducting what is available"
            )
            deduct = available

        inv.used = round(inv.used + deduct, 3)
        instance.material_consumed = True

        # Audit record for v1 deductions (mirrors v2 StockMovement)
        from ..models import MaterialUsage
        usage = MaterialUsage(
            customer_id=instance.component.assembly.drawing.customer_id,
            production_item_id=None,
            name=inv.name,
            qty=deduct,
            unit=inv.unit or "kg",
            by=f"v3-component-deduction (instance {instance.id})",
            applied=False,
        )
        db.add(usage)

        return {
            "success": True,
            "material_name": inv.name,
            "weight_deducted": deduct,
            "lot_number": None,
            "warnings": warnings,
        }

    @staticmethod
    def _get_stage_pipeline(
        db: Session, customer_id: Optional[int] = None
    ) -> list:
        """
        Return the ordered stage pipeline for a customer.

        Queries StageConfig first; falls back to DEFAULT_STAGES if none
        are configured.
        """
        configs = (
            db.query(StageConfig)
            .filter(StageConfig.customer_id == customer_id)
            .order_by(StageConfig.sequence.asc())
            .all()
        )

        if not configs:
            return [dict(s) for s in DEFAULT_STAGES]

        return [
            {
                "stage_name": c.stage_name,
                "sequence": c.sequence,
                "is_mandatory": c.is_mandatory,
                "auto_deduct_material": c.auto_deduct_material,
                "requires_qa_hold": c.requires_qa_hold,
            }
            for c in configs
        ]

    @staticmethod
    def _get_next_stage(pipeline: list, current_stage: str) -> Optional[str]:
        """
        Return the name of the next mandatory stage after current_stage.

        Returns "completed" if already at the final stage, or None if
        current_stage is not found in the pipeline.
        """
        names = [s["stage_name"] for s in pipeline]

        if current_stage not in names:
            return None

        idx = names.index(current_stage)
        remaining = pipeline[idx + 1:]

        for stage in remaining:
            if stage.get("is_mandatory", True):
                return stage["stage_name"]

        return "completed"

    @staticmethod
    def _validate_stage_order(
        pipeline: list, from_stage: str, to_stage: str
    ) -> None:
        """
        Raise ValueError when to_stage does not come after from_stage in
        the pipeline, or when to_stage is unknown.
        """
        names = [s["stage_name"] for s in pipeline]

        if to_stage == "completed":
            final_stage = names[-1] if names else None
            if final_stage and from_stage != final_stage:
                raise ValueError(
                    f"Cannot jump to 'completed' from '{from_stage}'. "
                    f"Must complete '{final_stage}' first."
                )
            return

        if to_stage not in names:
            raise ValueError(
                f"Stage '{to_stage}' is not in the pipeline. "
                f"Valid stages: {names}"
            )

        if from_stage in names and names.index(to_stage) <= names.index(from_stage):
            raise ValueError(
                f"Cannot move from '{from_stage}' to '{to_stage}' — "
                "target stage must come after the current stage"
            )

    @staticmethod
    def _update_drawing_progress(db: Session, instance: ComponentInstance) -> None:
        """
        Recalculate completed_weight_kg on the parent Drawing and update
        quantity_complete on each Assembly.

        If all instances across the drawing are complete, marks the drawing
        as COMPLETE and every assembly at full qty.
        """
        drawing = ComponentTrackingService._get_drawing_for_instance(db, instance)
        if not drawing:
            return

        rows = (
            db.query(ComponentInstance, Component)
            .join(Component, ComponentInstance.component_id == Component.id)
            .join(Assembly, Component.assembly_id == Assembly.id)
            .filter(Assembly.drawing_id == drawing.id)
            .all()
        )

        ComponentTrackingService._apply_progress_rollup(db, drawing, rows)

    @staticmethod
    def _get_drawing_for_instance(
        db: Session, instance: ComponentInstance
    ) -> Optional[Drawing]:
        """Navigate instance → component → assembly → drawing."""
        component = db.query(Component).filter(
            Component.id == instance.component_id
        ).first()
        if not component:
            return None
        assembly = db.query(Assembly).filter(
            Assembly.id == component.assembly_id
        ).first()
        if not assembly:
            return None
        return db.query(Drawing).filter(Drawing.id == assembly.drawing_id).first()

    @staticmethod
    def _apply_progress_rollup(db: Session, drawing: Drawing, rows: list) -> None:
        """Update completed_weight_kg, assembly counts, and drawing status."""
        total_count = len(rows)
        completed_count = sum(1 for inst, _ in rows if inst.is_completed)

        completed_weight = sum(
            float(comp.weight_each_kg) for inst, comp in rows if inst.is_completed
        )
        drawing.completed_weight_kg = Decimal(str(round(completed_weight, 3)))

        # assembly_id → [total, completed]
        asm_totals: dict = {}
        for inst, comp in rows:
            entry = asm_totals.setdefault(comp.assembly_id, [0, 0])
            entry[0] += 1
            if inst.is_completed:
                entry[1] += 1

        if total_count > 0 and completed_count == total_count:
            drawing.status = DrawingStatus.COMPLETE
            for asm in drawing.assemblies:
                asm.quantity_complete = asm.quantity_required
        else:
            for asm in drawing.assemblies:
                counts = asm_totals.get(asm.id, [0, 0])
                asm.quantity_complete = counts[1]

        db.flush()
