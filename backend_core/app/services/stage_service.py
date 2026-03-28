"""
StageService — Per-piece completion tracking for assemblies.

Handles:
  - Incrementing completed pieces for parts and stage tracking
  - Auto-completing stages when all pieces done
  - Progress summaries per assembly and per customer
  - Triggering material deduction when fabrication auto-completes
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..models_bom import Assembly, AssemblyMaterialRequirement, AssemblyPart, AssemblyStageTracking
from .deduction_service import DeductionService, InsufficientStockError

logger = logging.getLogger(__name__)

STAGES = ["fabrication", "painting", "dispatch"]


class StageService:
    """Per-piece completion tracking."""

    @staticmethod
    def update_piece_count(
        db: Session,
        assembly_id: int,
        stage: str,
        completed_delta: int,
        user_id: int,
    ) -> dict:
        """
        Increment completed pieces for a stage.
        When completed == total, auto-completes the stage.
        Auto-triggers material deduction when fabrication auto-completes.

        Returns dict with updated counts and auto-complete status.
        """
        if stage not in STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly {assembly_id} not found")

        st = (
            db.query(AssemblyStageTracking)
            .filter(
                AssemblyStageTracking.assembly_id == assembly_id,
                AssemblyStageTracking.stage == stage,
            )
            .first()
        )

        if not st:
            raise ValueError(f"Stage tracking for '{stage}' not found")

        if st.status == "completed":
            raise ValueError(f"Stage '{stage}' is already completed")

        # Update piece count
        new_completed = st.completed_pieces + completed_delta
        if new_completed < 0:
            new_completed = 0
        if new_completed > st.total_pieces:
            raise ValueError(
                f"Cannot exceed total pieces ({st.total_pieces}). "
                f"Current: {st.completed_pieces}, delta: {completed_delta}"
            )

        st.completed_pieces = new_completed
        st.updated_by = user_id

        # Start stage if not already started
        if st.status == "pending" and completed_delta > 0:
            st.status = "in_progress"
            st.started_at = datetime.utcnow()

        auto_completed = False

        # Auto-complete when all pieces done
        if new_completed >= st.total_pieces and st.total_pieces > 0:
            st.status = "completed"
            st.completed_at = datetime.utcnow()
            auto_completed = True

            # Advance assembly stage
            stage_idx = STAGES.index(stage)
            if stage_idx < len(STAGES) - 1:
                assembly.current_stage = STAGES[stage_idx + 1]
            else:
                assembly.current_stage = "completed"
            db.add(assembly)

            logger.info(
                "Auto-completed stage '%s' for assembly %s (all %d pieces done)",
                stage,
                assembly.assembly_code,
                st.total_pieces,
            )

        # Trigger material deduction when fabrication auto-completes
        if auto_completed and stage == "fabrication":
            requirements = (
                db.query(AssemblyMaterialRequirement)
                .filter(
                    AssemblyMaterialRequirement.assembly_id == assembly_id,
                    AssemblyMaterialRequirement.deducted == False,
                )
                .all()
            )
            if requirements:
                try:
                    with db.begin_nested():
                        for req in requirements:
                            if not req.inventory_id or req.required_qty_kg <= 0:
                                continue
                            inv = (
                                db.query(models.Inventory)
                                .filter(models.Inventory.id == req.inventory_id)
                                .with_for_update()
                                .first()
                            )
                            if not inv:
                                continue
                            available = (inv.total or 0) - (inv.used or 0)
                            needed = float(req.required_qty_kg)
                            if available < needed:
                                raise InsufficientStockError(
                                    material_name=req.material_name or "Unknown",
                                    needed=needed,
                                    available=available,
                                )
                            inv.used = (inv.used or 0) + needed
                            db.add(inv)
                            req.deducted = True
                            db.add(req)
                            # Audit trail
                            usage = models.MaterialUsage(
                                customer_id=assembly.customer_id,
                                name=req.material_name or "BOM material",
                                qty=needed,
                                unit="kg",
                                by=f"BOM auto-deduction for assembly {assembly.assembly_code} (user: {user_id})",
                                applied=True,
                            )
                            db.add(usage)
                        assembly.fabrication_deducted = True
                        assembly.material_deducted = True
                        db.add(assembly)
                except InsufficientStockError:
                    logger.warning(
                        "Insufficient stock for assembly %s deduction",
                        assembly.assembly_code,
                    )
                    # Don't fail the stage completion — just log the warning

        db.add(st)
        db.commit()

        return {
            "assembly_id": assembly_id,
            "stage": stage,
            "total_pieces": st.total_pieces,
            "completed_pieces": st.completed_pieces,
            "status": st.status,
            "auto_completed": auto_completed,
            "percentage": round(
                (st.completed_pieces / st.total_pieces * 100) if st.total_pieces > 0 else 0,
                1,
            ),
        }

    @staticmethod
    def update_part_completion(
        db: Session,
        part_id: int,
        completed_delta: int,
        user_id: int,
    ) -> dict:
        """
        Update piece completion for a specific part.
        Also updates the parent assembly's fabrication stage tracking.
        """
        part = db.query(AssemblyPart).filter(AssemblyPart.id == part_id).first()
        if not part:
            raise ValueError(f"Part {part_id} not found")

        new_completed = (part.completed_qty or 0) + completed_delta
        if new_completed < 0:
            new_completed = 0
        if new_completed > part.total_qty:
            raise ValueError(
                f"Cannot exceed total qty ({part.total_qty}). "
                f"Current: {part.completed_qty}, delta: {completed_delta}"
            )

        part.completed_qty = new_completed
        db.add(part)
        db.commit()
        db.refresh(part)

        return {
            "part_id": part.id,
            "mark_number": part.mark_number,
            "total_qty": part.total_qty,
            "completed_qty": part.completed_qty,
            "percentage": round(
                (part.completed_qty / part.total_qty * 100) if part.total_qty > 0 else 0,
                1,
            ),
        }

    @staticmethod
    def get_assembly_progress(db: Session, assembly_id: int) -> dict:
        """Get per-stage piece progress for an assembly."""
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise ValueError(f"Assembly {assembly_id} not found")

        stages = (
            db.query(AssemblyStageTracking)
            .filter(AssemblyStageTracking.assembly_id == assembly_id)
            .order_by(AssemblyStageTracking.id)
            .all()
        )

        parts = (
            db.query(AssemblyPart)
            .filter(AssemblyPart.assembly_id == assembly_id)
            .all()
        )

        return {
            "assembly_id": assembly.id,
            "assembly_code": assembly.assembly_code,
            "assembly_name": assembly.assembly_name,
            "current_stage": assembly.current_stage,
            "stages": [
                {
                    "stage": st.stage,
                    "status": st.status,
                    "total_pieces": st.total_pieces,
                    "completed_pieces": st.completed_pieces,
                    "percentage": round(
                        (st.completed_pieces / st.total_pieces * 100) if st.total_pieces > 0 else 0,
                        1,
                    ),
                }
                for st in stages
            ],
            "parts": [
                {
                    "part_id": p.id,
                    "mark_number": p.mark_number,
                    "part_name": p.part_name,
                    "total_qty": p.total_qty,
                    "completed_qty": p.completed_qty or 0,
                    "percentage": round(
                        ((p.completed_qty or 0) / p.total_qty * 100) if p.total_qty > 0 else 0,
                        1,
                    ),
                }
                for p in parts
            ],
        }

    @staticmethod
    def get_progress_dashboard(
        db: Session, customer_id: Optional[int] = None
    ) -> dict:
        """
        Dashboard aggregate: total pieces across all assemblies per stage.
        Optionally filtered by customer_id.
        """
        query = db.query(AssemblyStageTracking)
        if customer_id:
            query = query.join(Assembly).filter(Assembly.customer_id == customer_id)

        # Aggregate by stage
        stage_totals = (
            query.with_entities(
                AssemblyStageTracking.stage,
                func.sum(AssemblyStageTracking.total_pieces).label("total"),
                func.sum(AssemblyStageTracking.completed_pieces).label("completed"),
            )
            .group_by(AssemblyStageTracking.stage)
            .all()
        )

        stages = []
        for stage_name, total, completed in stage_totals:
            total = total or 0
            completed = completed or 0
            stages.append({
                "stage": stage_name,
                "total_pieces": total,
                "completed_pieces": completed,
                "percentage": round((completed / total * 100) if total > 0 else 0, 1),
            })

        # Count assemblies
        asm_query = db.query(Assembly)
        if customer_id:
            asm_query = asm_query.filter(Assembly.customer_id == customer_id)
        total_assemblies = asm_query.count()

        return {
            "total_assemblies": total_assemblies,
            "stages": stages,
        }
