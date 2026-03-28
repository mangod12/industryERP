"""
DeductionService — Consolidated Material Deduction Logic
==========================================================
Replaces THREE separate deduction code paths with a single, race-condition-safe
implementation.

Previous paths (all removed):
  1. tracking.py:_deduct_materials_for_fabrication() — on stage complete
  2. tracking_api.py:78  — checklist toggle FIFO deduction
  3. tracking_api.py:141 — stage advance FIFO deduction

Design:
  - SELECT FOR UPDATE on ProductionItem serializes concurrent requests
  - Idempotency check AFTER lock acquired (not before)
  - SAVEPOINT wraps all deductions for atomic rollback
  - Negative inventory is NEVER allowed (raises InsufficientStockError)
  - Both fabrication_deducted and material_deducted set atomically

Pattern reference: Follows inventory_service.py:StockLotService which already
uses with_for_update() correctly.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


class InsufficientStockError(Exception):
    """Raised when inventory has insufficient stock for deduction."""

    def __init__(self, material_name: str, needed: float, available: float):
        self.material_name = material_name
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient stock for '{material_name}': "
            f"need {needed:.2f}, only {available:.2f} available"
        )


@dataclass
class DeductionDetail:
    material_name: str
    material_id: int
    qty: float
    unit: Optional[str]


@dataclass
class DeductionResult:
    success: bool = False
    skipped: bool = False
    skipped_reason: Optional[str] = None
    deductions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class DeductionService:
    """Consolidated, race-condition-safe material deduction."""

    @staticmethod
    def deduct_materials_for_item(
        db: Session,
        production_item_id: int,
        user_id: int,
        trigger: str = "fabrication_complete",
    ) -> DeductionResult:
        """
        Deduct raw materials from inventory for a production item.

        Serializes concurrent requests via SELECT FOR UPDATE on the
        ProductionItem row, then performs idempotent FIFO deduction
        inside a SAVEPOINT.

        Args:
            db: Active database session (caller manages outer transaction)
            production_item_id: The production item to deduct for
            user_id: ID of the user triggering deduction
            trigger: Description of what triggered this deduction

        Returns:
            DeductionResult with success/skip status and deduction details

        Raises:
            InsufficientStockError: If any material has insufficient stock
                (entire deduction is rolled back)
        """
        result = DeductionResult()

        # 1. Acquire row-level lock to serialize concurrent requests.
        #    SQLite doesn't support FOR UPDATE, but serialized writes via
        #    its file-level lock achieve the same effect. For Postgres,
        #    with_for_update() provides true row-level locking.
        item = (
            db.query(models.ProductionItem)
            .filter(models.ProductionItem.id == production_item_id)
            .with_for_update()
            .first()
        )

        if item is None:
            result.skipped = True
            result.skipped_reason = "Production item not found"
            return result

        # 2. Idempotency check AFTER lock acquired — critical for race safety.
        #    If another thread already deducted, we see the updated flags.
        if item.fabrication_deducted or item.material_deducted:
            result.skipped = True
            result.skipped_reason = "Already deducted"
            return result

        # 3. Resolve material requirements
        material_reqs = DeductionService._resolve_material_requirements(item, db)

        if not material_reqs:
            result.skipped_reason = (
                "No material requirements set and no auto-match found"
            )
            # Notify boss
            notification = models.Notification(
                role="Boss",
                message=(
                    f"Item '{item.item_name}' (Code: {item.item_code}) completed "
                    f"fabrication but has no material link. No auto-deduction performed."
                ),
                level="warning",
            )
            db.add(notification)
            # Mark as deducted to prevent retry loops
            item.fabrication_deducted = True
            item.material_deducted = True
            db.add(item)
            return result

        # 4. SAVEPOINT wraps all deductions — atomic rollback on any failure
        with db.begin_nested():
            for req in material_reqs:
                material_id = req.get("material_id")
                qty = float(req.get("qty", 0))

                if not material_id or qty <= 0:
                    continue

                inv_item = (
                    db.query(models.Inventory)
                    .filter(models.Inventory.id == material_id)
                    .with_for_update()
                    .first()
                )

                if inv_item is None:
                    result.warnings.append(
                        f"Inventory item ID {material_id} not found"
                    )
                    continue

                available = (inv_item.total or 0) - (inv_item.used or 0)

                # NEVER allow negative inventory
                if available < qty:
                    raise InsufficientStockError(
                        material_name=inv_item.name,
                        needed=qty,
                        available=available,
                    )

                # Perform deduction
                inv_item.used = (inv_item.used or 0) + qty
                db.add(inv_item)

                # Create audit trail via MaterialUsage
                usage = models.MaterialUsage(
                    customer_id=item.customer_id,
                    production_item_id=item.id,
                    name=inv_item.name,
                    qty=qty,
                    unit=inv_item.unit,
                    by=f"Auto-deducted on {trigger} (user: {user_id})",
                    applied=True,
                )
                db.add(usage)
                db.flush()  # Get usage.id

                # Create consumption record for FIFO audit
                consumption = models.MaterialConsumption(
                    material_usage_id=usage.id,
                    inventory_id=inv_item.id,
                    qty=qty,
                )
                db.add(consumption)

                result.deductions.append(
                    DeductionDetail(
                        material_name=inv_item.name,
                        material_id=inv_item.id,
                        qty=qty,
                        unit=inv_item.unit,
                    )
                )

                logger.info(
                    "Deducted %.2f %s of '%s' for item %s (trigger: %s)",
                    qty,
                    inv_item.unit or "units",
                    inv_item.name,
                    item.item_code,
                    trigger,
                )

            # Set both flags atomically inside the savepoint
            item.fabrication_deducted = True
            item.material_deducted = True
            db.add(item)

        result.success = len(result.deductions) > 0
        return result

    @staticmethod
    def deduct_materials_fifo(
        db: Session,
        production_item_id: int,
        user_id: int,
        trigger: str = "checklist_complete",
    ) -> DeductionResult:
        """
        FIFO deduction path for tracking_api.py (checklist toggle / stage advance).

        Uses pending MaterialUsage rows (applied=False) and consumes from oldest
        inventory first. Same locking and idempotency guarantees.
        """
        result = DeductionResult()

        item = (
            db.query(models.ProductionItem)
            .filter(models.ProductionItem.id == production_item_id)
            .with_for_update()
            .first()
        )

        if item is None:
            result.skipped = True
            result.skipped_reason = "Production item not found"
            return result

        # Idempotency check AFTER lock
        if getattr(item, "material_deducted", False):
            result.skipped = True
            result.skipped_reason = "Already deducted"
            return result

        # Get pending material usage rows
        mu_rows = (
            db.query(models.MaterialUsage)
            .filter(
                models.MaterialUsage.production_item_id == item.id,
                models.MaterialUsage.applied == False,
            )
            .all()
        )

        if not mu_rows:
            result.skipped = True
            result.skipped_reason = "No pending material usage records"
            return result

        # SAVEPOINT for atomic deduction
        with db.begin_nested():
            for mu in mu_rows:
                needed = float(mu.qty or 0)
                if needed <= 0:
                    continue

                # FIFO: consume from oldest inventory rows first
                inv_rows = (
                    db.query(models.Inventory)
                    .filter(models.Inventory.name == mu.name)
                    .order_by(
                        models.Inventory.created_at.asc(),
                        models.Inventory.id.asc(),
                    )
                    .all()
                )

                if not inv_rows:
                    raise InsufficientStockError(
                        material_name=mu.name,
                        needed=needed,
                        available=0,
                    )

                remaining = needed
                for inv in inv_rows:
                    available = (inv.total or 0) - (inv.used or 0)
                    if available <= 0:
                        continue

                    take = min(available, remaining)
                    inv.used = (inv.used or 0) + float(take)
                    db.add(inv)

                    # Audit consumption record
                    cons = models.MaterialConsumption(
                        material_usage_id=mu.id,
                        inventory_id=inv.id,
                        qty=float(take),
                    )
                    db.add(cons)

                    result.deductions.append(
                        DeductionDetail(
                            material_name=inv.name,
                            material_id=inv.id,
                            qty=take,
                            unit=inv.unit,
                        )
                    )

                    remaining -= take
                    if remaining <= 1e-9:
                        break

                if remaining > 1e-9:
                    # Calculate total available across all rows
                    total_available = sum(
                        max(0, (inv.total or 0) - (inv.used or 0))
                        for inv in inv_rows
                    )
                    raise InsufficientStockError(
                        material_name=mu.name,
                        needed=needed,
                        available=total_available + (needed - remaining),
                    )

                mu.applied = True
                db.add(mu)

            # Set both flags atomically — must match deduct_materials_for_item behavior
            item.material_deducted = True
            item.fabrication_deducted = True
            db.add(item)

        result.success = len(result.deductions) > 0
        return result

    @staticmethod
    def _resolve_material_requirements(
        item: models.ProductionItem, db: Session
    ) -> list:
        """
        Resolve material requirements from JSON or auto-match by section.

        Returns list of dicts: [{"material_id": int, "qty": float}, ...]
        """
        # Try JSON requirements first
        if item.material_requirements:
            try:
                reqs = json.loads(item.material_requirements)
                if reqs:
                    return reqs
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid material_requirements JSON for item %s",
                    item.item_code,
                )

        # Auto-match by section name
        if item.section:
            from sqlalchemy import or_

            inv_item = (
                db.query(models.Inventory)
                .filter(
                    or_(
                        models.Inventory.name.ilike(f"%{item.section}%"),
                        models.Inventory.section.ilike(f"%{item.section}%"),
                    )
                )
                .first()
            )

            if inv_item:
                qty = (item.quantity or 1) * (item.weight_per_unit or 0)
                if qty > 0:
                    return [
                        {
                            "material_id": inv_item.id,
                            "qty": qty,
                            "inventory_name": inv_item.name,
                        }
                    ]

        return []
