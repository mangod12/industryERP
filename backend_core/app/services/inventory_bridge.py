"""
Inventory Bridge Service
========================
Bridges v1 inventory operations (Inventory.used mutations) into the v2 stock
ledger (StockMovement records on StockLots).

Feature-flagged: set V2_BRIDGE_ENABLED=true to activate.
Default off -- zero impact without opt-in.

Design:
- Never fails the v1 operation if the bridge fails -- log warning and continue.
- Same DB transaction for atomicity (caller controls commit).
- FIFO lot selection when multiple lots match a material.
"""

import logging
import os
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Inventory
from ..models_v2 import (
    MaterialMaster,
    MovementType,
    QAStatus,
    StockLot,
    StockMovement,
)
from .inventory_service import get_next_sequence
from .stock_valuation_service import StockValuationService

logger = logging.getLogger(__name__)

V2_BRIDGE_ENABLED = os.environ.get("V2_BRIDGE_ENABLED", "false").lower() == "true"

# Try to import accounting service (optional)
try:
    from .accounting_service import ACCOUNTING_ENABLED, AccountingService
except ImportError:
    ACCOUNTING_ENABLED = False
    AccountingService = None  # type: ignore[assignment, misc]


class InventoryBridgeService:
    """Bridges v1 inventory operations into v2 stock ledger."""

    @staticmethod
    def find_matching_v2_lot(
        db: Session, inventory_item: Inventory
    ) -> Optional[StockLot]:
        """Find a v2 StockLot matching a v1 Inventory item.

        Match strategy:
        1. Match by MaterialMaster.name ILIKE inventory_item.name
        2. If inventory_item.section is set, prefer MaterialMaster with matching category/sub_category
        3. From matched MaterialMaster, pick the oldest active, approved StockLot (FIFO)

        Returns the best matching active lot or None.
        """
        if not inventory_item or not inventory_item.name:
            return None

        inv_name = inventory_item.name.strip()

        # Build query for MaterialMaster matching by name (case-insensitive)
        mat_query = db.query(MaterialMaster).filter(
            MaterialMaster.is_active == True,
            func.lower(MaterialMaster.name) == inv_name.lower(),
        )

        material = mat_query.first()

        # Fallback: partial/LIKE match
        if material is None:
            material = (
                db.query(MaterialMaster)
                .filter(
                    MaterialMaster.is_active == True,
                    func.lower(MaterialMaster.name).contains(inv_name.lower()),
                )
                .first()
            )

        # If section is available, try matching by category
        if material is None and inventory_item.section:
            section = inventory_item.section.strip()
            material = (
                db.query(MaterialMaster)
                .filter(
                    MaterialMaster.is_active == True,
                    func.lower(MaterialMaster.category) == section.lower(),
                )
                .first()
            )

        if material is None:
            return None

        # Find oldest active, approved lot for this material (FIFO)
        lot = (
            db.query(StockLot)
            .filter(
                StockLot.material_id == material.id,
                StockLot.is_active == True,
                StockLot.is_blocked == False,
                StockLot.qa_status.in_([QAStatus.APPROVED, QAStatus.CONDITIONAL]),
                StockLot.current_weight_kg > 0,
            )
            .order_by(StockLot.received_date.asc())
            .first()
        )

        return lot

    @staticmethod
    def bridge_deduction(
        db: Session,
        inventory_item: Inventory,
        qty_deducted: float,
        reason: str,
        user_id: Optional[int] = None,
    ) -> Optional[StockMovement]:
        """After v1 deduction, create a matching v2 StockMovement.

        Steps:
        1. Find matching v2 lot
        2. If found, create CONSUMPTION movement with weight_change_kg
        3. Record valuation on movement
        4. Optionally create accounting entry
        5. If no matching lot found, log warning (don't fail)

        Returns the created StockMovement, or None if no match / bridge skipped.
        Never raises -- all errors are caught and logged.
        """
        lot = InventoryBridgeService.find_matching_v2_lot(db, inventory_item)

        if lot is None:
            logger.warning(
                "V2 bridge: no matching lot for v1 Inventory id=%s name='%s'. "
                "Skipping v2 movement creation.",
                inventory_item.id,
                inventory_item.name,
            )
            return None

        # Use a savepoint so that bridge failures don't poison the session
        savepoint = db.begin_nested()
        try:
            weight_kg = Decimal(str(qty_deducted)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )

            weight_before = lot.current_weight_kg
            weight_after = weight_before - weight_kg

            # Clamp to zero if we'd go negative (v1 allows negative, v2 doesn't)
            if weight_after < 0:
                logger.warning(
                    "V2 bridge: deduction of %.3f kg exceeds lot %s available %.3f kg. "
                    "Clamping to available.",
                    float(weight_kg),
                    lot.lot_number,
                    float(weight_before),
                )
                weight_kg = weight_before
                weight_after = Decimal("0")

            effective_user_id = user_id if user_id is not None else 0

            movement = StockMovement(
                movement_number=get_next_sequence(db, "movement", "MOV"),
                stock_lot_id=lot.id,
                movement_type=MovementType.CONSUMPTION,
                weight_change_kg=-weight_kg,
                weight_before_kg=weight_before,
                weight_after_kg=weight_after,
                reference_type="v1_bridge",
                reason=reason,
                from_location_id=lot.location_id,
                created_by=effective_user_id,
                movement_date=datetime.utcnow(),
            )
            db.add(movement)
            db.flush()

            # Record valuation
            StockValuationService.record_valuation_on_movement(db, movement, lot)

            # Optional accounting entry
            if ACCOUNTING_ENABLED and AccountingService is not None:
                try:
                    AccountingService.create_entry_for_stock_movement(db, movement)
                except Exception:
                    logger.warning(
                        "V2 bridge: accounting entry failed for movement %s",
                        movement.movement_number,
                        exc_info=True,
                    )

            # Update the lot weight
            lot.current_weight_kg = weight_after
            if lot.current_weight_kg <= Decimal("0"):
                lot.is_active = False
                lot.current_weight_kg = Decimal("0")
            lot.updated_at = datetime.utcnow()

            savepoint.commit()
            return movement

        except Exception:
            savepoint.rollback()
            logger.warning(
                "V2 bridge: unexpected error bridging deduction for Inventory id=%s. "
                "v1 deduction will proceed unaffected.",
                getattr(inventory_item, "id", "?"),
                exc_info=True,
            )
            return None

    @staticmethod
    def get_reconciliation_report(db: Session) -> dict:
        """Compare v1 Inventory quantities with v2 StockLot totals.

        For each v1 Inventory item, tries to find matching MaterialMaster
        entries and sums their active lot weights.

        Returns:
            {
                "matched": [...],   # v1 items with a v2 counterpart
                "drifted": [...],   # matched but quantities differ
                "v1_only": [...],   # in v1 but not v2
                "v2_only": [...],   # in v2 but not v1
            }
        """
        matched = []
        drifted = []
        v1_only = []

        # Get all v1 inventory items
        v1_items = db.query(Inventory).all()

        # Track which materials we've matched from v2
        matched_material_ids: set[int] = set()

        for inv in v1_items:
            v1_available = (inv.total or 0) - (inv.used or 0)
            inv_name = (inv.name or "").strip()

            # Try to find matching MaterialMaster
            material = (
                db.query(MaterialMaster)
                .filter(
                    MaterialMaster.is_active == True,
                    func.lower(MaterialMaster.name) == inv_name.lower(),
                )
                .first()
            )

            if material is None:
                # Try partial match
                material = (
                    db.query(MaterialMaster)
                    .filter(
                        MaterialMaster.is_active == True,
                        func.lower(MaterialMaster.name).contains(inv_name.lower()),
                    )
                    .first()
                )

            if material is None:
                v1_only.append(
                    {
                        "v1_id": inv.id,
                        "name": inv.name,
                        "v1_total": inv.total,
                        "v1_used": inv.used,
                        "v1_available": round(v1_available, 3),
                    }
                )
                continue

            matched_material_ids.add(material.id)

            # Sum v2 lot weights for this material
            v2_total_kg = (
                db.query(func.sum(StockLot.current_weight_kg))
                .filter(
                    StockLot.material_id == material.id,
                    StockLot.is_active == True,
                )
                .scalar()
            )
            v2_total = float(v2_total_kg) if v2_total_kg else 0.0

            entry = {
                "v1_id": inv.id,
                "v2_material_id": material.id,
                "name": inv.name,
                "material_code": material.code,
                "v1_available": round(v1_available, 3),
                "v2_available_kg": round(v2_total, 3),
                "drift_kg": round(v2_total - v1_available, 3),
            }

            # Consider drifted if difference > 0.5 kg
            if abs(v2_total - v1_available) > 0.5:
                drifted.append(entry)
            else:
                matched.append(entry)

        # Find v2-only materials (have active lots but no v1 match)
        v2_only = []
        all_v2_material_ids = (
            db.query(StockLot.material_id)
            .filter(StockLot.is_active == True)
            .distinct()
            .all()
        )

        for (mat_id,) in all_v2_material_ids:
            if mat_id in matched_material_ids:
                continue

            material = (
                db.query(MaterialMaster)
                .filter(MaterialMaster.id == mat_id)
                .first()
            )
            if material is None:
                continue

            v2_total_kg = (
                db.query(func.sum(StockLot.current_weight_kg))
                .filter(
                    StockLot.material_id == mat_id,
                    StockLot.is_active == True,
                )
                .scalar()
            )

            v2_only.append(
                {
                    "v2_material_id": mat_id,
                    "material_code": material.code,
                    "name": material.name,
                    "v2_available_kg": round(float(v2_total_kg or 0), 3),
                }
            )

        return {
            "matched": matched,
            "drifted": drifted,
            "v1_only": v1_only,
            "v2_only": v2_only,
            "summary": {
                "matched_count": len(matched),
                "drifted_count": len(drifted),
                "v1_only_count": len(v1_only),
                "v2_only_count": len(v2_only),
            },
        }
