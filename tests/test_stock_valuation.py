"""
Unit tests for StockValuationService — FIFO valuation, weighted average,
record_valuation_on_movement, fiscal year, balance tracking, and summaries.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from backend_core.app.models_v2 import (
    MaterialMaster,
    MaterialType,
    MovementType,
    QAStatus,
    StockLot,
    StockMovement,
    Vendor,
)
from backend_core.app.services.inventory_service import (
    StockLotService,
    get_next_sequence,
)
from backend_core.app.services.stock_valuation_service import StockValuationService
from tests.conftest import create_test_stock_lot, create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_material(db, code="VAL-MAT-01", name="HR Plate", rate=None):
    mat = MaterialMaster(code=code, name=name, material_type=MaterialType.PLATE)
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


def _create_vendor(db, code="V-VAL-01", name="Steel Corp"):
    vendor = Vendor(code=code, name=name)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def _create_lot(
    db,
    material_id,
    vendor_id,
    *,
    lot_number,
    weight_kg,
    purchase_rate=None,
    received_date=None,
    qa_status=QAStatus.APPROVED,
):
    """Create a StockLot with specific weight and purchase rate."""
    wt = Decimal(str(weight_kg))
    lot = StockLot(
        lot_number=lot_number,
        material_id=material_id,
        vendor_id=vendor_id,
        gross_weight_kg=wt + Decimal("10"),
        tare_weight_kg=Decimal("10"),
        net_weight_kg=wt,
        current_weight_kg=wt,
        purchase_rate=Decimal(str(purchase_rate)) if purchase_rate is not None else None,
        qa_status=qa_status,
        received_date=received_date or datetime.utcnow(),
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


# ===========================================================================
# TestFiscalYear
# ===========================================================================


class TestFiscalYear:
    """Tests for StockValuationService.get_fiscal_year()"""

    def test_april_2025_is_fy2526(self):
        assert StockValuationService.get_fiscal_year(date(2025, 4, 1)) == "FY2526"

    def test_march_2026_is_fy2526(self):
        assert StockValuationService.get_fiscal_year(date(2026, 3, 31)) == "FY2526"

    def test_january_2025_is_fy2425(self):
        assert StockValuationService.get_fiscal_year(date(2025, 1, 15)) == "FY2425"

    def test_december_2025_is_fy2526(self):
        assert StockValuationService.get_fiscal_year(date(2025, 12, 31)) == "FY2526"

    def test_april_2000_is_fy0001(self):
        assert StockValuationService.get_fiscal_year(date(2000, 4, 1)) == "FY0001"

    def test_march_2001_is_fy0001(self):
        assert StockValuationService.get_fiscal_year(date(2001, 3, 31)) == "FY0001"


# ===========================================================================
# TestValuationRateForLot
# ===========================================================================


class TestValuationRateForLot:
    def test_returns_purchase_rate(self, db):
        mat = _create_material(db, code="VR-MAT-01")
        vendor = _create_vendor(db, code="V-VR-01")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="VR-LOT-01",
            weight_kg=100,
            purchase_rate=45.50,
        )
        rate = StockValuationService.get_valuation_rate_for_lot(lot)
        assert rate == Decimal("45.5000")

    def test_returns_zero_when_no_rate(self, db):
        mat = _create_material(db, code="VR-MAT-02")
        vendor = _create_vendor(db, code="V-VR-02")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="VR-LOT-02",
            weight_kg=100,
            purchase_rate=None,
        )
        rate = StockValuationService.get_valuation_rate_for_lot(lot)
        assert rate == Decimal("0")

    def test_returns_zero_when_rate_is_zero(self, db):
        mat = _create_material(db, code="VR-MAT-03")
        vendor = _create_vendor(db, code="V-VR-03")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="VR-LOT-03",
            weight_kg=100,
            purchase_rate=0,
        )
        rate = StockValuationService.get_valuation_rate_for_lot(lot)
        assert rate == Decimal("0")


# ===========================================================================
# TestFIFOValuation
# ===========================================================================


class TestFIFOValuation:
    """FIFO valuation: 3 lots at different rates, verify value calculation."""

    def test_fifo_three_lots_different_rates(self, db):
        mat = _create_material(db, code="FIFO-V-01")
        vendor = _create_vendor(db, code="V-FIFO-V-01")

        # Lot 1: 100 kg @ 50/kg = 5000
        _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="FIFO-L1",
            weight_kg=100,
            purchase_rate=50,
            received_date=datetime.utcnow() - timedelta(days=30),
        )
        # Lot 2: 200 kg @ 55/kg = 11000
        _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="FIFO-L2",
            weight_kg=200,
            purchase_rate=55,
            received_date=datetime.utcnow() - timedelta(days=20),
        )
        # Lot 3: 150 kg @ 60/kg = 9000
        _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="FIFO-L3",
            weight_kg=150,
            purchase_rate=60,
            received_date=datetime.utcnow() - timedelta(days=10),
        )

        result = StockValuationService.calculate_fifo_valuation(db, mat.id)

        assert result["total_qty_kg"] == 450.0
        assert result["total_value"] == 25000.0  # 5000 + 11000 + 9000
        assert len(result["lot_breakdown"]) == 3
        # Oldest lot should come first
        assert result["lot_breakdown"][0]["lot_number"] == "FIFO-L1"

    def test_fifo_after_partial_consumption(self, db):
        """After consuming 80 kg from oldest lot, FIFO value should update."""
        mat = _create_material(db, code="FIFO-V-02")
        vendor = _create_vendor(db, code="V-FIFO-V-02")

        lot1 = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="FIFO-PC-L1",
            weight_kg=100,
            purchase_rate=50,
            received_date=datetime.utcnow() - timedelta(days=30),
        )
        _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="FIFO-PC-L2",
            weight_kg=200,
            purchase_rate=60,
            received_date=datetime.utcnow() - timedelta(days=10),
        )

        # Simulate partial consumption
        lot1.current_weight_kg = Decimal("20.000")
        db.commit()

        result = StockValuationService.calculate_fifo_valuation(db, mat.id)

        # 20*50 + 200*60 = 1000 + 12000 = 13000
        assert result["total_qty_kg"] == 220.0
        assert result["total_value"] == 13000.0


# ===========================================================================
# TestWeightedAvgValuation
# ===========================================================================


class TestWeightedAvgValuation:
    def test_weighted_avg_three_lots(self, db):
        mat = _create_material(db, code="WA-MAT-01")
        vendor = _create_vendor(db, code="V-WA-01")

        _create_lot(db, mat.id, vendor.id, lot_number="WA-L1", weight_kg=100, purchase_rate=50)
        _create_lot(db, mat.id, vendor.id, lot_number="WA-L2", weight_kg=200, purchase_rate=55)
        _create_lot(db, mat.id, vendor.id, lot_number="WA-L3", weight_kg=150, purchase_rate=60)

        result = StockValuationService.calculate_weighted_avg_valuation(db, mat.id)

        assert result["total_qty_kg"] == 450.0
        assert result["total_value"] == 25000.0
        # avg = 25000 / 450 = 55.5556
        assert abs(result["avg_rate_per_kg"] - 55.5556) < 0.001

    def test_weighted_avg_single_lot(self, db):
        mat = _create_material(db, code="WA-MAT-02")
        vendor = _create_vendor(db, code="V-WA-02")

        _create_lot(db, mat.id, vendor.id, lot_number="WA-S1", weight_kg=500, purchase_rate=42)

        result = StockValuationService.calculate_weighted_avg_valuation(db, mat.id)

        assert result["total_qty_kg"] == 500.0
        assert result["total_value"] == 21000.0
        assert result["avg_rate_per_kg"] == 42.0

    def test_weighted_avg_no_stock(self, db):
        mat = _create_material(db, code="WA-MAT-03")

        result = StockValuationService.calculate_weighted_avg_valuation(db, mat.id)

        assert result["total_qty_kg"] == 0.0
        assert result["total_value"] == 0.0
        assert result["avg_rate_per_kg"] == 0.0


# ===========================================================================
# TestRecordValuationOnMovement
# ===========================================================================


class TestRecordValuationOnMovement:
    def test_all_fields_populated(self, db):
        user = create_test_user(db)
        mat = _create_material(db, code="RV-MAT-01")
        vendor = _create_vendor(db, code="V-RV-01")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="RV-LOT-01",
            weight_kg=500,
            purchase_rate=45,
        )

        movement = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.INWARD_PURCHASE,
            weight_change_kg=Decimal("500.000"),
            weight_before_kg=Decimal("0"),
            weight_after_kg=Decimal("500.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(movement)
        db.flush()

        StockValuationService.record_valuation_on_movement(db, movement, lot)

        assert movement.valuation_rate == Decimal("45.0000")
        assert movement.stock_value_change == Decimal("22500.00")
        assert movement.balance_qty_kg is not None
        assert movement.balance_stock_value is not None
        assert movement.posting_date == date.today()
        assert movement.fiscal_year is not None

    def test_posting_date_override(self, db):
        user = create_test_user(db)
        mat = _create_material(db, code="RV-MAT-02")
        vendor = _create_vendor(db, code="V-RV-02")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="RV-LOT-02",
            weight_kg=100,
            purchase_rate=30,
        )

        movement = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.INWARD_PURCHASE,
            weight_change_kg=Decimal("100.000"),
            weight_before_kg=Decimal("0"),
            weight_after_kg=Decimal("100.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(movement)
        db.flush()

        override_date = date(2025, 2, 15)
        StockValuationService.record_valuation_on_movement(db, movement, lot, posting_date_override=override_date)

        assert movement.posting_date == override_date
        assert movement.fiscal_year == "FY2425"

    def test_negative_consumption_movement(self, db):
        user = create_test_user(db)
        mat = _create_material(db, code="RV-MAT-03")
        vendor = _create_vendor(db, code="V-RV-03")
        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="RV-LOT-03",
            weight_kg=500,
            purchase_rate=40,
        )

        movement = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.CONSUMPTION,
            weight_change_kg=Decimal("-100.000"),
            weight_before_kg=Decimal("500.000"),
            weight_after_kg=Decimal("400.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(movement)
        db.flush()

        StockValuationService.record_valuation_on_movement(db, movement, lot)

        assert movement.valuation_rate == Decimal("40.0000")
        assert movement.stock_value_change == Decimal("-4000.00")


# ===========================================================================
# TestBalanceTracking
# ===========================================================================


class TestBalanceTracking:
    """Sequence of movements, verify running totals."""

    def test_running_balances_across_movements(self, db):
        """Test that balance_qty_kg and balance_stock_value track running totals.

        The cold-start logic in _get_latest_balance computes from active lots,
        so the first movement's balance = lot.current_weight_kg + weight_change.
        We create the lot with current_weight_kg matching the inward so that
        the cold-start base is already that value, then track consumption deltas.
        """
        user = create_test_user(db)
        mat = _create_material(db, code="BAL-MAT-01")
        vendor = _create_vendor(db, code="V-BAL-01")

        lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="BAL-LOT-01",
            weight_kg=1000,
            purchase_rate=50,
        )

        # Movement 1: record the inward of the lot that already exists.
        # Cold-start balance = lot.current_weight_kg (1000) * rate (50) = 50000
        # weight_change = +1000, so new balance = 1000 + 1000 = 2000 (but that
        # double-counts).  Instead, just record a consumption movement directly
        # since the lot already exists with 1000 kg.

        # Movement 1: consume 200 kg (balance goes from 1000 -> 800)
        m1 = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.CONSUMPTION,
            weight_change_kg=Decimal("-200.000"),
            weight_before_kg=Decimal("1000.000"),
            weight_after_kg=Decimal("800.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(m1)
        db.flush()
        StockValuationService.record_valuation_on_movement(db, m1, lot)

        # Cold-start: 1000 kg * 50 = 50000, then -200*50 = -10000 => 800, 40000
        assert m1.balance_qty_kg == Decimal("800.000")
        assert m1.balance_stock_value == Decimal("40000.00")

        # Movement 2: consume 300 kg more (balance: 800 -> 500)
        m2 = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.CONSUMPTION,
            weight_change_kg=Decimal("-300.000"),
            weight_before_kg=Decimal("800.000"),
            weight_after_kg=Decimal("500.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(m2)
        db.flush()
        StockValuationService.record_valuation_on_movement(db, m2, lot)

        assert m2.balance_qty_kg == Decimal("500.000")
        assert m2.balance_stock_value == Decimal("25000.00")

        # Movement 3: consume 100 kg more (balance: 500 -> 400)
        m3 = StockMovement(
            movement_number=get_next_sequence(db, "movement", "MOV"),
            stock_lot_id=lot.id,
            movement_type=MovementType.CONSUMPTION,
            weight_change_kg=Decimal("-100.000"),
            weight_before_kg=Decimal("500.000"),
            weight_after_kg=Decimal("400.000"),
            created_by=user.id,
            movement_date=datetime.utcnow(),
        )
        db.add(m3)
        db.flush()
        StockValuationService.record_valuation_on_movement(db, m3, lot)

        assert m3.balance_qty_kg == Decimal("400.000")
        assert m3.balance_stock_value == Decimal("20000.00")


# ===========================================================================
# TestZeroPurchaseRate
# ===========================================================================


class TestZeroPurchaseRate:
    def test_zero_rate_gives_zero_value(self, db):
        mat = _create_material(db, code="ZR-MAT-01")
        vendor = _create_vendor(db, code="V-ZR-01")
        _lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="ZR-LOT-01",
            weight_kg=500,
            purchase_rate=0,
        )

        result = StockValuationService.calculate_fifo_valuation(db, mat.id)
        assert result["total_value"] == 0.0
        assert result["total_qty_kg"] == 500.0

    def test_none_rate_gives_zero_value(self, db):
        mat = _create_material(db, code="ZR-MAT-02")
        vendor = _create_vendor(db, code="V-ZR-02")
        _lot = _create_lot(
            db,
            mat.id,
            vendor.id,
            lot_number="ZR-LOT-02",
            weight_kg=300,
            purchase_rate=None,
        )

        result = StockValuationService.calculate_weighted_avg_valuation(db, mat.id)
        assert result["total_value"] == 0.0
        assert result["avg_rate_per_kg"] == 0.0


# ===========================================================================
# TestStockValueSummary
# ===========================================================================


class TestStockValueSummary:
    def test_summary_across_materials(self, db):
        mat1 = _create_material(db, code="SV-MAT-01", name="Plate A")
        mat2 = _create_material(db, code="SV-MAT-02", name="Plate B")
        vendor = _create_vendor(db, code="V-SV-01")

        _create_lot(db, mat1.id, vendor.id, lot_number="SV-L1", weight_kg=100, purchase_rate=50)
        _create_lot(db, mat2.id, vendor.id, lot_number="SV-L2", weight_kg=200, purchase_rate=60)

        results = StockValuationService.get_stock_value_summary(db, method="fifo")

        assert len(results) == 2
        codes = {r["material_code"] for r in results}
        assert "SV-MAT-01" in codes
        assert "SV-MAT-02" in codes

        for r in results:
            assert r["method"] == "fifo"
            assert r["total_value"] > 0

    def test_summary_weighted_avg(self, db):
        mat = _create_material(db, code="SV-MAT-03")
        vendor = _create_vendor(db, code="V-SV-02")

        _create_lot(db, mat.id, vendor.id, lot_number="SV-WA-L1", weight_kg=100, purchase_rate=40)
        _create_lot(db, mat.id, vendor.id, lot_number="SV-WA-L2", weight_kg=100, purchase_rate=60)

        results = StockValuationService.get_stock_value_summary(db, method="weighted_avg")

        assert len(results) == 1
        r = results[0]
        assert r["method"] == "weighted_avg"
        assert r["total_value"] == 10000.0  # 100*40 + 100*60
        assert r["rate_per_kg"] == 50.0  # 10000 / 200

    def test_summary_excludes_inactive_lots(self, db):
        mat = _create_material(db, code="SV-MAT-04")
        vendor = _create_vendor(db, code="V-SV-03")

        lot = _create_lot(db, mat.id, vendor.id, lot_number="SV-IN-L1", weight_kg=100, purchase_rate=50)
        lot.is_active = False
        db.commit()

        results = StockValuationService.get_stock_value_summary(db, method="fifo")
        mat_ids = [r["material_id"] for r in results]
        assert mat.id not in mat_ids


# ===========================================================================
# TestIntegrationWithInventoryService
# ===========================================================================


class TestIntegrationWithInventoryService:
    """Verify that valuation fields are populated when using inventory service methods."""

    def test_consume_populates_valuation(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("500.000"),
            current_weight_kg=Decimal("500.000"),
            purchase_rate=Decimal("45.00"),
        )

        movement, updated_lot = StockLotService.consume_from_lot(
            db, lot.id, Decimal("100"), user.id, "Test consumption"
        )
        db.commit()

        assert movement.valuation_rate == Decimal("45.0000")
        assert movement.stock_value_change == Decimal("-4500.00")
        assert movement.posting_date is not None
        assert movement.fiscal_year is not None

    def test_adjust_stock_populates_valuation(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("1000.000"),
            gross_weight_kg=Decimal("1010.000"),
            current_weight_kg=Decimal("400.000"),
            purchase_rate=Decimal("30.00"),
        )

        movement, updated_lot = StockLotService.adjust_stock(
            db, lot.id, Decimal("450.000"), user.id, "Reweigh correction"
        )
        db.commit()

        assert movement.valuation_rate == Decimal("30.0000")
        assert movement.stock_value_change == Decimal("1500.00")  # +50 kg * 30
        assert movement.posting_date is not None
