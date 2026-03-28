"""
Unit tests for DeductionService — the consolidated material deduction logic.

Tests:
  - Happy path: successful deduction with correct inventory/audit updates
  - Already deducted: idempotent skip
  - Insufficient stock: raises InsufficientStockError, no partial deduction
  - No material requirements: skip with notification
  - Auto-match by section: fallback when no JSON requirements
  - FIFO deduction: consumes from pending MaterialUsage rows
"""
import json
import pytest

from app import models
from app.services.deduction_service import (
    DeductionService,
    InsufficientStockError,
    DeductionResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer(db):
    c = models.Customer(name="Test Customer", project_details="Test")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_inventory(db, name="40 NB(M) PIPE", total=1000.0, used=0.0):
    inv = models.Inventory(name=name, unit="kg", total=total, used=used, section=name)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _make_production_item(db, customer_id, inv_id=None, qty=1.0, weight=3.09, section="40 NB(M) PIPE"):
    reqs = None
    if inv_id:
        reqs = json.dumps([{"material_id": inv_id, "qty": qty * weight}])
    item = models.ProductionItem(
        customer_id=customer_id,
        item_code="HR110-01",
        item_name="Top Rail",
        section=section,
        length_mm=868,
        quantity=qty,
        weight_per_unit=weight,
        material_requirements=reqs,
        current_stage="fabrication",
        fabrication_deducted=False,
        material_deducted=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Tests: deduct_materials_for_item (JSON requirements path)
# ---------------------------------------------------------------------------

class TestDeductMaterialsForItem:
    """Tests for the primary deduction path (tracking.py complete_stage)."""

    def test_happy_path(self, db_session, boss_user):
        """Successful deduction reduces inventory and sets flags."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, total=100.0, used=0.0)
        item = _make_production_item(db, cust.id, inv_id=inv.id, qty=2.0, weight=5.0)

        result = DeductionService.deduct_materials_for_item(
            db=db, production_item_id=item.id, user_id=boss_user.id
        )
        db.commit()

        assert result.success is True
        assert len(result.deductions) == 1
        assert result.deductions[0].qty == 10.0  # 2 * 5.0

        # Verify inventory updated
        db.refresh(inv)
        assert inv.used == 10.0

        # Verify flags set
        db.refresh(item)
        assert item.fabrication_deducted is True
        assert item.material_deducted is True

    def test_already_deducted_is_idempotent(self, db_session, boss_user):
        """Calling deduction on already-deducted item is a no-op."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, total=100.0)
        item = _make_production_item(db, cust.id, inv_id=inv.id)

        # First deduction
        DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)
        db.commit()

        # Second call should skip
        result = DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)
        assert result.skipped is True
        assert result.skipped_reason == "Already deducted"

        # Inventory should not change again
        db.refresh(inv)
        assert inv.used == 3.09  # Only deducted once

    def test_insufficient_stock_raises_error(self, db_session, boss_user):
        """InsufficientStockError raised when inventory is too low."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, total=5.0, used=4.0)  # Only 1.0 available
        item = _make_production_item(db, cust.id, inv_id=inv.id, qty=1.0, weight=3.09)

        with pytest.raises(InsufficientStockError) as exc_info:
            DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)

        assert "40 NB(M) PIPE" in str(exc_info.value)

        # Inventory must be UNCHANGED (savepoint rollback)
        db.refresh(inv)
        assert inv.used == 4.0  # No change

        # Flags must remain False
        db.refresh(item)
        assert item.fabrication_deducted is False
        assert item.material_deducted is False

    def test_no_requirements_creates_notification(self, db_session, boss_user):
        """Item with no material requirements creates boss notification."""
        db = db_session
        cust = _make_customer(db)
        item = _make_production_item(db, cust.id, section=None)
        # No material_requirements JSON, no section → no auto-match

        result = DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)
        db.commit()

        assert result.success is False
        assert "no material" in (result.skipped_reason or "").lower()

        # Should still mark as deducted to prevent retry
        db.refresh(item)
        assert item.fabrication_deducted is True

        # Verify notification created
        notif = db.query(models.Notification).filter(
            models.Notification.role == "Boss"
        ).first()
        assert notif is not None
        assert item.item_name in notif.message

    def test_auto_match_by_section(self, db_session, boss_user):
        """Auto-matches inventory by section when no JSON requirements."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, name="40 NB(M) PIPE", total=100.0)
        item = _make_production_item(
            db, cust.id, inv_id=None, section="40 NB(M) PIPE", qty=1.0, weight=3.09
        )

        result = DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)
        db.commit()

        assert result.success is True
        db.refresh(inv)
        assert inv.used == pytest.approx(3.09, abs=0.01)

    def test_item_not_found(self, db_session, boss_user):
        """Non-existent item ID returns skipped result."""
        result = DeductionService.deduct_materials_for_item(
            db_session, production_item_id=99999, user_id=boss_user.id
        )
        assert result.skipped is True
        assert "not found" in (result.skipped_reason or "").lower()


# ---------------------------------------------------------------------------
# Tests: deduct_materials_fifo (MaterialUsage-based path)
# ---------------------------------------------------------------------------

class TestDeductMaterialsFifo:
    """Tests for the FIFO deduction path (tracking_api.py checklist/stage)."""

    def test_fifo_happy_path(self, db_session, boss_user):
        """FIFO deduction processes pending MaterialUsage rows."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, name="Steel Plate", total=500.0)
        item = _make_production_item(db, cust.id, section="Steel Plate")

        # Create pending MaterialUsage
        mu = models.MaterialUsage(
            customer_id=cust.id,
            production_item_id=item.id,
            name="Steel Plate",
            qty=50.0,
            unit="kg",
            applied=False,
        )
        db.add(mu)
        db.commit()

        result = DeductionService.deduct_materials_fifo(
            db, item.id, boss_user.id, trigger="checklist_complete"
        )
        db.commit()

        assert result.success is True
        db.refresh(inv)
        assert inv.used == 50.0
        db.refresh(mu)
        assert mu.applied is True
        db.refresh(item)
        assert item.material_deducted is True

    def test_fifo_insufficient_stock(self, db_session, boss_user):
        """FIFO raises InsufficientStockError when stock too low."""
        db = db_session
        cust = _make_customer(db)
        inv = _make_inventory(db, name="Steel Plate", total=10.0, used=0.0)
        item = _make_production_item(db, cust.id)

        mu = models.MaterialUsage(
            customer_id=cust.id,
            production_item_id=item.id,
            name="Steel Plate",
            qty=50.0,
            unit="kg",
            applied=False,
        )
        db.add(mu)
        db.commit()

        with pytest.raises(InsufficientStockError):
            DeductionService.deduct_materials_fifo(db, item.id, boss_user.id)

        # Inventory unchanged
        db.refresh(inv)
        assert inv.used == 0.0

    def test_fifo_already_deducted(self, db_session, boss_user):
        """FIFO skips if material_deducted already set."""
        db = db_session
        cust = _make_customer(db)
        item = _make_production_item(db, cust.id)
        item.material_deducted = True
        db.add(item)
        db.commit()

        result = DeductionService.deduct_materials_fifo(db, item.id, boss_user.id)
        assert result.skipped is True

    def test_fifo_no_pending_usage(self, db_session, boss_user):
        """FIFO skips when no pending MaterialUsage records."""
        db = db_session
        cust = _make_customer(db)
        item = _make_production_item(db, cust.id)

        result = DeductionService.deduct_materials_fifo(db, item.id, boss_user.id)
        assert result.skipped is True
        assert "no pending" in (result.skipped_reason or "").lower()

    def test_fifo_consumes_oldest_first(self, db_session, boss_user):
        """FIFO consumes from oldest inventory row first."""
        db = db_session
        cust = _make_customer(db)

        # Create two inventory rows for same material
        inv_old = _make_inventory(db, name="Beam", total=30.0)
        inv_new = _make_inventory(db, name="Beam", total=100.0)

        item = _make_production_item(db, cust.id, section="Beam")
        mu = models.MaterialUsage(
            customer_id=cust.id,
            production_item_id=item.id,
            name="Beam",
            qty=40.0,
            unit="kg",
            applied=False,
        )
        db.add(mu)
        db.commit()

        result = DeductionService.deduct_materials_fifo(db, item.id, boss_user.id)
        db.commit()

        assert result.success is True
        db.refresh(inv_old)
        db.refresh(inv_new)
        # Should take all 30 from old, then 10 from new
        assert inv_old.used == 30.0
        assert inv_new.used == 10.0
