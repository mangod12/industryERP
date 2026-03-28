"""
Regression test: Inventory must NEVER go negative.

The old code at tracking.py:94 allowed negative inventory with the comment
"admin can adjust". DeductionService now prevents this.
"""
import json
import pytest

from app import models
from app.services.deduction_service import DeductionService, InsufficientStockError


def _setup(db, total=50.0, used=45.0, needed=10.0):
    """Create customer + inventory (5.0 available) + item needing 10.0."""
    customer = models.Customer(name="Negative Test Customer")
    db.add(customer)
    db.flush()

    inv = models.Inventory(
        name="Steel Bar", unit="kg", total=total, used=used, section="Steel Bar"
    )
    db.add(inv)
    db.flush()

    reqs = json.dumps([{"material_id": inv.id, "qty": needed}])
    item = models.ProductionItem(
        customer_id=customer.id,
        item_code="NEG-01",
        item_name="Negative Test Item",
        section="Steel Bar",
        quantity=1.0,
        weight_per_unit=needed,
        material_requirements=reqs,
        current_stage="fabrication",
        fabrication_deducted=False,
        material_deducted=False,
    )
    db.add(item)
    db.commit()
    return customer, inv, item


class TestNegativeInventoryPrevention:
    """Verify that DeductionService never allows inventory.used > inventory.total."""

    def test_deduction_refused_when_stock_insufficient(self, db_session, boss_user):
        """Deduction is refused when available < needed."""
        db = db_session
        cust, inv, item = _setup(db, total=50.0, used=45.0, needed=10.0)

        with pytest.raises(InsufficientStockError) as exc:
            DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)

        assert exc.value.available == pytest.approx(5.0)
        assert exc.value.needed == pytest.approx(10.0)

        # Inventory MUST be unchanged
        db.refresh(inv)
        assert inv.used == 45.0
        assert (inv.total - inv.used) == 5.0  # Still 5.0 available

    def test_deduction_refused_when_fully_consumed(self, db_session, boss_user):
        """Deduction refused when inventory is fully consumed (0 available)."""
        db = db_session
        cust, inv, item = _setup(db, total=100.0, used=100.0, needed=1.0)

        with pytest.raises(InsufficientStockError):
            DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)

        db.refresh(inv)
        assert inv.used == 100.0

    def test_exact_available_succeeds(self, db_session, boss_user):
        """Deduction succeeds when available exactly equals needed."""
        db = db_session
        cust, inv, item = _setup(db, total=100.0, used=90.0, needed=10.0)

        result = DeductionService.deduct_materials_for_item(db, item.id, boss_user.id)
        db.commit()

        assert result.success is True
        db.refresh(inv)
        assert inv.used == 100.0  # Exactly consumed
        assert (inv.total - inv.used) == 0.0

    def test_fifo_refuses_negative(self, db_session, boss_user):
        """FIFO path also refuses when stock insufficient."""
        db = db_session
        customer = models.Customer(name="FIFO Neg Test")
        db.add(customer)
        db.flush()

        inv = models.Inventory(name="Angle", unit="kg", total=20.0, used=18.0)
        db.add(inv)
        db.flush()

        item = models.ProductionItem(
            customer_id=customer.id,
            item_code="FNEG-01",
            item_name="FIFO Neg Test Item",
            current_stage="fabrication",
            fabrication_deducted=False,
            material_deducted=False,
            item_code_prefix="",
        ) if False else models.ProductionItem(
            customer_id=customer.id,
            item_code="FNEG-01",
            item_name="FIFO Neg Test Item",
            current_stage="fabrication",
            fabrication_deducted=False,
            material_deducted=False,
        )
        db.add(item)
        db.flush()

        mu = models.MaterialUsage(
            customer_id=customer.id,
            production_item_id=item.id,
            name="Angle",
            qty=5.0,
            unit="kg",
            applied=False,
        )
        db.add(mu)
        db.commit()

        with pytest.raises(InsufficientStockError):
            DeductionService.deduct_materials_fifo(db, item.id, boss_user.id)

        db.refresh(inv)
        assert inv.used == 18.0  # Unchanged
