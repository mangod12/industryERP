"""
Unit tests for InventoryService — StockLotService, InventoryQueryService,
weight conversion helpers, and GRN service.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend_core.app.models_v2 import (
    DocumentStatus,
    GoodsReceiptNote,
    GRNLineItem,
    MaterialMaster,
    MaterialType,
    MovementType,
    QAStatus,
    StockLot,
    StockMovement,
    StorageLocation,
    Vendor,
    WeightUnit,
)
from backend_core.app.services.inventory_service import (
    GRNService,
    InsufficientStockError,
    InvalidOperationError,
    InventoryQueryService,
    StockLotService,
    get_next_sequence,
    kg_to_tons,
    normalize_weight,
    tons_to_kg,
)
from tests.conftest import (
    create_test_stock_lot,
    create_test_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_material(db, code="MAT-001", name="HR Coil", mat_type=MaterialType.COIL):
    mat = MaterialMaster(code=code, name=name, material_type=mat_type)
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


def _create_vendor(db, code="V-001", name="Steel Corp"):
    vendor = Vendor(code=code, name=name)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def _create_location(db, code="WH1-A-01", name="Warehouse 1 Rack A"):
    loc = StorageLocation(code=code, name=name, location_type="warehouse")
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _create_grn_with_line(
    db,
    vendor_id,
    material_id,
    user_id,
    weight_kg=Decimal("500.000"),
    received_qty=Decimal("1"),
    qa_status=QAStatus.APPROVED,
    status=DocumentStatus.SUBMITTED,
):
    grn = GoodsReceiptNote(
        grn_number=f"GRN-TEST-{datetime.utcnow().timestamp()}",
        vendor_id=vendor_id,
        status=status,
        gate_entry_time=datetime.utcnow(),
        created_by=user_id,
    )
    db.add(grn)
    db.flush()

    line = GRNLineItem(
        grn_id=grn.id,
        material_id=material_id,
        received_qty=received_qty,
        weight_kg=weight_kg,
        unit=WeightUnit.KG,
        qa_status=qa_status,
    )
    db.add(line)
    db.commit()
    db.refresh(grn)
    return grn, line


# ===========================================================================
# TestWeightConversions
# ===========================================================================


class TestWeightConversions:
    """Tests for kg_to_tons, tons_to_kg, normalize_weight."""

    def test_kg_to_tons_basic(self):
        assert kg_to_tons(Decimal("1000")) == Decimal("1.000")

    def test_kg_to_tons_precision(self):
        assert kg_to_tons(Decimal("1500.500")) == Decimal("1.501")

    def test_kg_to_tons_zero(self):
        assert kg_to_tons(Decimal("0")) == Decimal("0.000")

    def test_tons_to_kg_basic(self):
        assert tons_to_kg(Decimal("1")) == Decimal("1000.000")

    def test_tons_to_kg_fractional(self):
        assert tons_to_kg(Decimal("2.5")) == Decimal("2500.000")

    def test_normalize_weight_kg_passthrough(self):
        result = normalize_weight(500.0, WeightUnit.KG)
        assert result == Decimal("500.000")

    def test_normalize_weight_ton_to_kg(self):
        result = normalize_weight(2, WeightUnit.TON)
        assert result == Decimal("2000.000")

    def test_normalize_weight_mt_to_kg(self):
        result = normalize_weight("1.5", WeightUnit.MT)
        assert result == Decimal("1500.000")

    def test_normalize_weight_piece_passthrough(self):
        result = normalize_weight(10, WeightUnit.PIECE)
        assert result == Decimal("10.000")


# ===========================================================================
# TestNumberSequence
# ===========================================================================


class TestNumberSequence:
    def test_get_next_sequence_creates_new(self, db):
        seq1 = get_next_sequence(db, "test_seq", "TST")
        assert "TST" in seq1
        assert "/000001" in seq1

    def test_get_next_sequence_increments(self, db):
        _seq1 = get_next_sequence(db, "test_seq2", "TST")
        seq2 = get_next_sequence(db, "test_seq2", "TST")
        # Second should end with 000002
        assert seq2.endswith("/000002")

    def test_get_next_sequence_no_year(self, db):
        seq = get_next_sequence(db, "test_no_year", "NTY", year_wise=False)
        assert "NTY/" in seq
        # Should not contain a year segment
        parts = seq.split("/")
        assert len(parts) == 2  # PREFIX/NUMBER


# ===========================================================================
# TestStockLotConsumption
# ===========================================================================


class TestStockLotConsumption:
    """Tests for StockLotService.consume_from_lot()"""

    def test_consume_reduces_weight_and_creates_movement(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, net_weight_kg=Decimal("500.000"), current_weight_kg=Decimal("500.000"))

        movement, updated_lot = StockLotService.consume_from_lot(
            db, lot.id, Decimal("100"), user.id, "Test consumption"
        )
        db.commit()

        assert updated_lot.current_weight_kg == Decimal("400.000")
        assert movement.movement_type == MovementType.CONSUMPTION
        assert movement.weight_change_kg == Decimal("-100.000")
        assert movement.weight_before_kg == Decimal("500.000")
        assert movement.weight_after_kg == Decimal("400.000")

    def test_consume_full_lot_marks_inactive(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, net_weight_kg=Decimal("100.000"), current_weight_kg=Decimal("100.000"))

        movement, updated_lot = StockLotService.consume_from_lot(
            db, lot.id, Decimal("100"), user.id, "Full consumption"
        )
        db.commit()

        assert updated_lot.current_weight_kg == Decimal("0")
        assert updated_lot.is_active is False

    def test_consume_insufficient_stock_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, net_weight_kg=Decimal("50.000"), current_weight_kg=Decimal("50.000"))

        with pytest.raises(InsufficientStockError, match="Insufficient stock"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("100"), user.id, "Over-consumption")

    def test_consume_blocked_lot_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db)
        lot.is_blocked = True
        lot.block_reason = "Dispute with vendor"
        db.commit()

        with pytest.raises(InvalidOperationError, match="blocked"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("10"), user.id, "Test")

    def test_consume_qa_pending_lot_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, qa_status=QAStatus.PENDING)

        with pytest.raises(InvalidOperationError, match="not QA approved"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("10"), user.id, "Test")

    def test_consume_qa_rejected_lot_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, qa_status=QAStatus.REJECTED)

        with pytest.raises(InvalidOperationError, match="not QA approved"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("10"), user.id, "Test")

    def test_consume_qa_on_hold_lot_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, qa_status=QAStatus.ON_HOLD)

        with pytest.raises(InvalidOperationError, match="not QA approved"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("10"), user.id, "Test")

    def test_consume_qa_conditional_lot_succeeds(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, qa_status=QAStatus.CONDITIONAL)

        movement, updated_lot = StockLotService.consume_from_lot(
            db, lot.id, Decimal("10"), user.id, "Conditional consume"
        )
        db.commit()

        assert movement is not None
        assert updated_lot.current_weight_kg < lot.net_weight_kg

    def test_consume_inactive_lot_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, net_weight_kg=Decimal("100.000"), current_weight_kg=Decimal("100.000"))
        lot.is_active = False
        db.commit()

        with pytest.raises(InvalidOperationError, match="not active"):
            StockLotService.consume_from_lot(db, lot.id, Decimal("10"), user.id, "Test")


# ===========================================================================
# TestStockAdjustment
# ===========================================================================


class TestStockAdjustment:
    """Tests for StockLotService.adjust_stock()"""

    def test_positive_adjustment_increases_weight(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("1000.000"),
            gross_weight_kg=Decimal("1010.000"),
            current_weight_kg=Decimal("400.000"),
        )

        movement, updated_lot = StockLotService.adjust_stock(
            db, lot.id, Decimal("450.000"), user.id, "Reweigh correction"
        )
        db.commit()

        assert updated_lot.current_weight_kg == Decimal("450.000")
        assert movement.movement_type == MovementType.ADJUSTMENT_PLUS
        assert movement.weight_before_kg == Decimal("400.000")
        assert movement.weight_after_kg == Decimal("450.000")

    def test_negative_adjustment_requires_approval(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("500.000"),
            current_weight_kg=Decimal("500.000"),
        )

        with pytest.raises(InvalidOperationError, match="require approval"):
            StockLotService.adjust_stock(db, lot.id, Decimal("400.000"), user.id, "Correction")

    def test_negative_adjustment_with_approval_succeeds(self, db):
        user = create_test_user(db)
        approver = create_test_user(db, role="Boss")
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("500.000"),
            current_weight_kg=Decimal("500.000"),
        )

        movement, updated_lot = StockLotService.adjust_stock(
            db,
            lot.id,
            Decimal("400.000"),
            user.id,
            "Correction",
            approved_by=approver.id,
        )
        db.commit()

        assert updated_lot.current_weight_kg == Decimal("400.000")
        assert movement.movement_type == MovementType.ADJUSTMENT_MINUS

    def test_zero_change_adjustment_raises_error(self, db):
        user = create_test_user(db)
        lot = create_test_stock_lot(db, current_weight_kg=Decimal("500.000"))

        with pytest.raises(InvalidOperationError, match="No weight change"):
            StockLotService.adjust_stock(db, lot.id, Decimal("500.000"), user.id, "No change")

    def test_adjustment_to_zero_marks_inactive(self, db):
        user = create_test_user(db)
        approver = create_test_user(db, role="Boss")
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("100.000"),
            current_weight_kg=Decimal("100.000"),
        )

        movement, updated_lot = StockLotService.adjust_stock(
            db,
            lot.id,
            Decimal("0"),
            user.id,
            "Write off",
            approved_by=approver.id,
        )
        db.commit()

        assert updated_lot.is_active is False
        assert updated_lot.current_weight_kg == Decimal("0")


# ===========================================================================
# TestFIFOPick
# ===========================================================================


class TestFIFOPick:
    """Tests for InventoryQueryService.get_lots_for_fifo_pick()"""

    def test_fifo_picks_oldest_lot_first(self, db):
        mat = _create_material(db, code="FIFO-MAT-01", name="HR Plate")

        # Create two lots: older one first
        vendor = _create_vendor(db, code="V-FIFO-01")
        old_lot = StockLot(
            lot_number="LOT-OLD",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow() - timedelta(days=30),
        )
        new_lot = StockLot(
            lot_number="LOT-NEW",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow(),
        )
        db.add_all([old_lot, new_lot])
        db.commit()

        picks = InventoryQueryService.get_lots_for_fifo_pick(db, mat.id, Decimal("300"))

        assert len(picks) == 1
        picked_lot, pick_weight = picks[0]
        assert picked_lot.lot_number == "LOT-OLD"
        assert pick_weight == Decimal("300")

    def test_fifo_spans_multiple_lots(self, db):
        mat = _create_material(db, code="FIFO-MAT-02")
        vendor = _create_vendor(db, code="V-FIFO-02")

        lot1 = StockLot(
            lot_number="LOT-SPAN-1",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("210"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("200"),
            current_weight_kg=Decimal("200"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow() - timedelta(days=10),
        )
        lot2 = StockLot(
            lot_number="LOT-SPAN-2",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("310"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("300"),
            current_weight_kg=Decimal("300"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow() - timedelta(days=5),
        )
        db.add_all([lot1, lot2])
        db.commit()

        picks = InventoryQueryService.get_lots_for_fifo_pick(db, mat.id, Decimal("350"))

        assert len(picks) == 2
        assert picks[0][0].lot_number == "LOT-SPAN-1"
        assert picks[0][1] == Decimal("200")
        assert picks[1][0].lot_number == "LOT-SPAN-2"
        assert picks[1][1] == Decimal("150")

    def test_fifo_insufficient_total_raises_error(self, db):
        mat = _create_material(db, code="FIFO-MAT-03")
        vendor = _create_vendor(db, code="V-FIFO-03")

        lot = StockLot(
            lot_number="LOT-SHORT",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("110"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("100"),
            current_weight_kg=Decimal("100"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow(),
        )
        db.add(lot)
        db.commit()

        with pytest.raises(InsufficientStockError, match="Cannot fulfill"):
            InventoryQueryService.get_lots_for_fifo_pick(db, mat.id, Decimal("200"))

    def test_fifo_skips_blocked_lots(self, db):
        mat = _create_material(db, code="FIFO-MAT-04")
        vendor = _create_vendor(db, code="V-FIFO-04")

        blocked_lot = StockLot(
            lot_number="LOT-BLOCKED",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            qa_status=QAStatus.APPROVED,
            is_blocked=True,
            received_date=datetime.utcnow() - timedelta(days=30),
        )
        good_lot = StockLot(
            lot_number="LOT-GOOD",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            qa_status=QAStatus.APPROVED,
            received_date=datetime.utcnow(),
        )
        db.add_all([blocked_lot, good_lot])
        db.commit()

        picks = InventoryQueryService.get_lots_for_fifo_pick(db, mat.id, Decimal("100"))

        assert len(picks) == 1
        assert picks[0][0].lot_number == "LOT-GOOD"


# ===========================================================================
# TestStockSummary
# ===========================================================================


class TestStockSummary:
    def test_get_stock_summary_returns_aggregated_data(self, db):
        mat = _create_material(db, code="SUM-MAT-01", name="Summary Plate")
        _lot1 = create_test_stock_lot(db, material_id=mat.id, current_weight_kg=Decimal("200.000"))
        _lot2 = create_test_stock_lot(db, material_id=mat.id, current_weight_kg=Decimal("300.000"))

        results = InventoryQueryService.get_stock_summary(db, material_id=mat.id)

        assert len(results) == 1
        assert results[0]["material_code"] == "SUM-MAT-01"
        assert results[0]["lot_count"] == 2
        assert results[0]["total_weight_kg"] == 500.0

    def test_get_stock_summary_excludes_inactive_by_default(self, db):
        mat = _create_material(db, code="SUM-MAT-02")
        lot = create_test_stock_lot(db, material_id=mat.id, current_weight_kg=Decimal("100.000"))
        lot.is_active = False
        db.commit()

        results = InventoryQueryService.get_stock_summary(db, material_id=mat.id)
        assert len(results) == 0

    def test_get_stock_summary_includes_inactive_when_requested(self, db):
        mat = _create_material(db, code="SUM-MAT-03")
        lot = create_test_stock_lot(db, material_id=mat.id, current_weight_kg=Decimal("100.000"))
        lot.is_active = False
        db.commit()

        results = InventoryQueryService.get_stock_summary(db, material_id=mat.id, include_inactive=True)
        assert len(results) == 1


# ===========================================================================
# TestReconciliation
# ===========================================================================


class TestReconciliation:
    def test_reconcile_within_tolerance(self, db):
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("1000.000"),
            gross_weight_kg=Decimal("1010.000"),
            current_weight_kg=Decimal("1000.000"),
        )

        result = InventoryQueryService.reconcile_physical_vs_system(db, lot.id, Decimal("1003.000"))

        assert result["within_tolerance"] is True
        assert result["requires_adjustment"] is False

    def test_reconcile_outside_tolerance(self, db):
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("1000.000"),
            gross_weight_kg=Decimal("1010.000"),
            current_weight_kg=Decimal("1000.000"),
        )

        result = InventoryQueryService.reconcile_physical_vs_system(db, lot.id, Decimal("900.000"))

        assert result["within_tolerance"] is False
        assert result["requires_adjustment"] is True
        assert result["variance_kg"] == -100.0

    def test_reconcile_exact_match(self, db):
        lot = create_test_stock_lot(db, current_weight_kg=Decimal("500.000"))

        result = InventoryQueryService.reconcile_physical_vs_system(db, lot.id, Decimal("500.000"))

        assert result["variance_kg"] == 0.0
        assert result["within_tolerance"] is True


# ===========================================================================
# TestGRNService
# ===========================================================================


class TestGRNService:
    def test_create_grn_in_draft_status(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-01")

        grn = GRNService.create_grn(db, vendor.id, user.id, vehicle_number="MH12AB1234")
        db.commit()

        assert grn.status == DocumentStatus.DRAFT
        assert grn.vehicle_number == "MH12AB1234"
        assert grn.grn_number is not None

    def test_add_line_item_to_draft_grn(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-02")
        mat = _create_material(db, code="GRN-MAT-01")

        grn = GRNService.create_grn(db, vendor.id, user.id)
        db.flush()

        line = GRNService.add_line_item(
            db,
            grn.id,
            mat.id,
            received_qty=Decimal("5"),
            weight_kg=Decimal("2500.000"),
            heat_number="HT-001",
        )
        db.commit()

        assert line.grn_id == grn.id
        assert line.qa_status == QAStatus.PENDING

    def test_add_line_to_non_draft_grn_raises_error(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-03")
        mat = _create_material(db, code="GRN-MAT-02")

        grn = GRNService.create_grn(db, vendor.id, user.id)
        grn.status = DocumentStatus.SUBMITTED
        db.commit()

        with pytest.raises(InvalidOperationError, match="draft"):
            GRNService.add_line_item(
                db,
                grn.id,
                mat.id,
                received_qty=Decimal("1"),
                weight_kg=Decimal("100.000"),
            )

    def test_approve_grn_creates_stock_lots(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-04")
        mat = _create_material(db, code="GRN-MAT-03")
        loc = _create_location(db, code="WH-GRN-01")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            weight_kg=Decimal("500.000"),
            qa_status=QAStatus.APPROVED,
            status=DocumentStatus.SUBMITTED,
        )

        grn_result, lots = GRNService.approve_grn(db, grn.id, user.id, loc.id)
        db.commit()

        assert grn_result.status == DocumentStatus.APPROVED
        assert len(lots) == 1
        assert lots[0].current_weight_kg == Decimal("500.000")
        assert lots[0].material_id == mat.id

    def test_approve_grn_rejects_pending_qa_items(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-05")
        mat = _create_material(db, code="GRN-MAT-04")
        loc = _create_location(db, code="WH-GRN-02")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            qa_status=QAStatus.PENDING,
            status=DocumentStatus.SUBMITTED,
        )

        with pytest.raises(InvalidOperationError, match="pending QA"):
            GRNService.approve_grn(db, grn.id, user.id, loc.id)

    def test_approve_grn_not_submitted_raises_error(self, db):
        user = create_test_user(db)
        vendor = _create_vendor(db, code="V-GRN-06")
        mat = _create_material(db, code="GRN-MAT-05")
        loc = _create_location(db, code="WH-GRN-03")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            qa_status=QAStatus.APPROVED,
            status=DocumentStatus.DRAFT,
        )

        with pytest.raises(InvalidOperationError, match="submitted before approval"):
            GRNService.approve_grn(db, grn.id, user.id, loc.id)


# ===========================================================================
# TestCreateLotFromGRN
# ===========================================================================


class TestCreateLotFromGRN:
    def test_create_lot_from_grn_creates_lot_and_movement(self, db):
        user = create_test_user(db)
        mat = _create_material(db, code="LOT-MAT-01")
        vendor = _create_vendor(db, code="V-LOT-01")
        loc = _create_location(db, code="WH-LOT-01")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            weight_kg=Decimal("750.000"),
            received_qty=Decimal("3"),
        )

        lot = StockLotService.create_lot_from_grn(db, line, loc.id, user.id)
        db.commit()

        assert lot.lot_number is not None
        assert lot.current_weight_kg == Decimal("750.000")
        assert lot.location_id == loc.id

        # Check movement was created
        movements = db.query(StockMovement).filter_by(stock_lot_id=lot.id).all()
        assert len(movements) == 1
        assert movements[0].movement_type == MovementType.INWARD_PURCHASE
        assert movements[0].weight_after_kg == Decimal("750.000")
