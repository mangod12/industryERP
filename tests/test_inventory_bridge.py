"""
Unit tests for InventoryBridgeService -- v1/v2 inventory bridge (Phase 4.4).

Covers:
- find_matching_v2_lot: exact match, partial match, section match, no match
- bridge_deduction: creates StockMovement, records valuation, handles no-match
- bridge_deduction: same transaction rollback rolls back both v1 and v2
- Reconciliation report: matched, drifted, v1-only, v2-only
- Feature flag off: no bridge operations
- Integration: advance_stage with V2_BRIDGE_ENABLED creates both deductions
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from backend_core.app.models import MaterialUsage, StageTracking
from backend_core.app.models_v2 import (
    MaterialMaster,
    MaterialType,
    MovementType,
    QAStatus,
    StockLot,
    StockMovement,
)
from backend_core.app.services.inventory_bridge import InventoryBridgeService
from backend_core.app.services.tracking_service import TrackingService
from tests.conftest import (
    create_test_customer,
    create_test_inventory,
    create_test_production_item,
    create_test_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_material_and_lot(
    db,
    name="Steel Plate",
    code="MAT-BRIDGE-001",
    weight_kg=Decimal("500.000"),
    category=None,
):
    """Create a MaterialMaster + active StockLot for bridge tests."""
    mat = MaterialMaster(
        code=code,
        name=name,
        material_type=MaterialType.PLATE,
        category=category,
        is_active=True,
    )
    db.add(mat)
    db.flush()

    from backend_core.app.models_v2 import Vendor

    vendor = Vendor(code=f"V-BR-{mat.id}", name="Bridge Test Vendor")
    db.add(vendor)
    db.flush()

    lot = StockLot(
        lot_number=f"LOT-BR-{mat.id:06d}",
        material_id=mat.id,
        vendor_id=vendor.id,
        gross_weight_kg=weight_kg + Decimal("10"),
        tare_weight_kg=Decimal("10"),
        net_weight_kg=weight_kg,
        current_weight_kg=weight_kg,
        received_date=datetime.utcnow(),
        qa_status=QAStatus.APPROVED,
        is_active=True,
        is_blocked=False,
    )
    db.add(lot)
    db.flush()
    return mat, lot


# ===========================================================================
# Test find_matching_v2_lot
# ===========================================================================


class TestFindMatchingV2Lot:
    """Tests for InventoryBridgeService.find_matching_v2_lot()"""

    def test_exact_name_match(self, db):
        mat, lot = _create_material_and_lot(db, name="ISMC 200", code="MAT-ISMC200")
        inv = create_test_inventory(db, name="ISMC 200", total=1000.0, used=0.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is not None
        assert result.id == lot.id

    def test_case_insensitive_match(self, db):
        mat, lot = _create_material_and_lot(db, name="Steel Beam", code="MAT-BEAM01")
        inv = create_test_inventory(db, name="steel beam", total=500.0, used=0.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is not None
        assert result.id == lot.id

    def test_returns_none_when_no_match(self, db):
        inv = create_test_inventory(db, name="NonExistentMaterial999", total=100.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is None

    def test_returns_none_for_none_input(self, db):
        result = InventoryBridgeService.find_matching_v2_lot(db, None)
        assert result is None

    def test_fifo_oldest_lot_selected(self, db):
        """When multiple lots match, the oldest (FIFO) is returned."""
        mat = MaterialMaster(
            code="MAT-FIFO-01",
            name="FIFO Material",
            material_type=MaterialType.BAR,
            is_active=True,
        )
        db.add(mat)
        db.flush()

        from backend_core.app.models_v2 import Vendor

        vendor = Vendor(code="V-FIFO-01", name="FIFO Vendor")
        db.add(vendor)
        db.flush()

        # Older lot
        old_lot = StockLot(
            lot_number="LOT-FIFO-OLD",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("300"),
            received_date=datetime(2024, 1, 1),
            qa_status=QAStatus.APPROVED,
            is_active=True,
        )
        # Newer lot
        new_lot = StockLot(
            lot_number="LOT-FIFO-NEW",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            received_date=datetime(2025, 6, 1),
            qa_status=QAStatus.APPROVED,
            is_active=True,
        )
        db.add_all([old_lot, new_lot])
        db.flush()

        inv = create_test_inventory(db, name="FIFO Material", total=800.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is not None
        assert result.id == old_lot.id

    def test_skips_blocked_lots(self, db):
        mat = MaterialMaster(
            code="MAT-BLOCKED-01",
            name="Blocked Material",
            material_type=MaterialType.PLATE,
            is_active=True,
        )
        db.add(mat)
        db.flush()

        from backend_core.app.models_v2 import Vendor

        vendor = Vendor(code="V-BLOCKED-01", name="Blocked Vendor")
        db.add(vendor)
        db.flush()

        blocked_lot = StockLot(
            lot_number="LOT-BLOCKED-01",
            material_id=mat.id,
            vendor_id=vendor.id,
            gross_weight_kg=Decimal("510"),
            tare_weight_kg=Decimal("10"),
            net_weight_kg=Decimal("500"),
            current_weight_kg=Decimal("500"),
            received_date=datetime.utcnow(),
            qa_status=QAStatus.APPROVED,
            is_active=True,
            is_blocked=True,
            block_reason="Dispute",
        )
        db.add(blocked_lot)
        db.flush()

        inv = create_test_inventory(db, name="Blocked Material", total=500.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is None

    def test_section_fallback_match(self, db):
        """When name doesn't match, falls back to section->category matching."""
        mat, lot = _create_material_and_lot(db, name="Category Match", code="MAT-CAT-01", category="angle")
        inv = create_test_inventory(db, name="Completely Different Name", section="angle", total=200.0)

        result = InventoryBridgeService.find_matching_v2_lot(db, inv)

        assert result is not None
        assert result.id == lot.id


# ===========================================================================
# Test bridge_deduction
# ===========================================================================


class TestBridgeDeduction:
    """Tests for InventoryBridgeService.bridge_deduction()"""

    def test_creates_stock_movement(self, db):
        mat, lot = _create_material_and_lot(db, name="Bridge Steel", code="MAT-BR-01")
        inv = create_test_inventory(db, name="Bridge Steel", total=1000.0, used=0.0)
        user = create_test_user(db)

        movement = InventoryBridgeService.bridge_deduction(db, inv, 50.0, "fabrication:123", user.id)

        assert movement is not None
        assert movement.movement_type == MovementType.CONSUMPTION
        assert float(movement.weight_change_kg) == -50.0
        assert movement.reference_type == "v1_bridge"
        assert movement.reason == "fabrication:123"
        assert movement.created_by == user.id

    def test_updates_lot_weight(self, db):
        mat, lot = _create_material_and_lot(db, name="Lot Weight Steel", code="MAT-LW-01", weight_kg=Decimal("500"))
        inv = create_test_inventory(db, name="Lot Weight Steel", total=1000.0)
        user = create_test_user(db)

        InventoryBridgeService.bridge_deduction(db, inv, 100.0, "fabrication:456", user.id)
        db.flush()

        db.expire(lot)
        assert lot.current_weight_kg == Decimal("400.000")

    def test_records_valuation(self, db):
        mat, lot = _create_material_and_lot(db, name="Valued Steel", code="MAT-VAL-01")
        lot.purchase_rate = Decimal("45.00")
        db.flush()

        inv = create_test_inventory(db, name="Valued Steel", total=1000.0)
        user = create_test_user(db)

        movement = InventoryBridgeService.bridge_deduction(db, inv, 10.0, "fabrication:789", user.id)

        assert movement is not None
        assert movement.valuation_rate is not None
        assert movement.stock_value_change is not None
        assert movement.posting_date is not None
        assert movement.fiscal_year is not None

    def test_no_matching_lot_logs_warning_no_failure(self, db):
        inv = create_test_inventory(db, name="Orphan Material XYZ", total=100.0)
        user = create_test_user(db)

        # Should not raise
        movement = InventoryBridgeService.bridge_deduction(db, inv, 10.0, "fabrication:999", user.id)

        assert movement is None

    def test_clamps_when_exceeding_lot_weight(self, db):
        mat, lot = _create_material_and_lot(db, name="Low Stock Steel", code="MAT-LOW-01", weight_kg=Decimal("20"))
        inv = create_test_inventory(db, name="Low Stock Steel", total=1000.0)
        user = create_test_user(db)

        movement = InventoryBridgeService.bridge_deduction(db, inv, 100.0, "fabrication:big", user.id)

        assert movement is not None
        # Should clamp to available 20 kg
        assert float(movement.weight_change_kg) == -20.0

        db.flush()
        db.expire(lot)
        assert lot.current_weight_kg == Decimal("0")
        assert lot.is_active is False

    def test_same_transaction_rollback(self, db):
        """Rollback undoes both v1 and v2 changes."""
        mat, lot = _create_material_and_lot(db, name="Rollback Steel", code="MAT-RB-01", weight_kg=Decimal("500"))
        inv = create_test_inventory(db, name="Rollback Steel", total=1000.0, used=0.0)
        user = create_test_user(db)

        initial_lot_weight = lot.current_weight_kg

        # Perform v1 deduction
        inv.used = (inv.used or 0) + 50.0
        db.add(inv)

        # Perform v2 bridge
        movement = InventoryBridgeService.bridge_deduction(db, inv, 50.0, "fabrication:rollback", user.id)

        assert movement is not None

        # Rollback the transaction
        db.rollback()

        # Both should be reverted
        db.refresh(inv)
        assert inv.used == 0.0

        db.refresh(lot)
        assert lot.current_weight_kg == initial_lot_weight

        # Movement should not exist
        count = db.query(StockMovement).filter(StockMovement.reference_type == "v1_bridge").count()
        assert count == 0

    def test_bridge_with_no_user_id_returns_none_gracefully(self, db):
        """Bridge with user_id=None should not crash (FK constraint
        prevents inserting with user 0, but the bridge catches all errors)."""
        mat, lot = _create_material_and_lot(db, name="NoUser Steel", code="MAT-NU-01")
        inv = create_test_inventory(db, name="NoUser Steel", total=1000.0)

        # user_id=None -> created_by=0 -> FK violation -> caught by try/except
        movement = InventoryBridgeService.bridge_deduction(db, inv, 10.0, "fabrication:noid", None)

        # Bridge should gracefully return None (error caught internally)
        assert movement is None


# ===========================================================================
# Test reconciliation report
# ===========================================================================


class TestReconciliationReport:
    """Tests for InventoryBridgeService.get_reconciliation_report()"""

    def test_matched_items(self, db):
        """Items with matching v1 and v2 quantities appear in 'matched'."""
        mat, lot = _create_material_and_lot(db, name="Matched Steel", code="MAT-MATCH-01", weight_kg=Decimal("500"))
        inv = create_test_inventory(db, name="Matched Steel", total=500.0, used=0.0)

        report = InventoryBridgeService.get_reconciliation_report(db)

        assert len(report["matched"]) >= 1
        match = next((m for m in report["matched"] if m["v1_id"] == inv.id), None)
        assert match is not None
        assert match["v2_material_id"] == mat.id
        assert abs(match["drift_kg"]) <= 0.5

    def test_drifted_items(self, db):
        """Items with significant quantity differences appear in 'drifted'."""
        mat, lot = _create_material_and_lot(db, name="Drifted Steel", code="MAT-DRIFT-01", weight_kg=Decimal("500"))
        # v1 says 300 available, v2 has 500 -> drift of 200
        inv = create_test_inventory(db, name="Drifted Steel", total=500.0, used=200.0)

        report = InventoryBridgeService.get_reconciliation_report(db)

        assert len(report["drifted"]) >= 1
        drifted = next((d for d in report["drifted"] if d["v1_id"] == inv.id), None)
        assert drifted is not None
        assert abs(drifted["drift_kg"] - 200.0) < 1.0

    def test_v1_only_items(self, db):
        """Items only in v1 (no v2 match) appear in 'v1_only'."""
        inv = create_test_inventory(db, name="OnlyInV1Material", total=100.0, used=10.0)

        report = InventoryBridgeService.get_reconciliation_report(db)

        assert len(report["v1_only"]) >= 1
        v1_item = next((v for v in report["v1_only"] if v["v1_id"] == inv.id), None)
        assert v1_item is not None
        assert v1_item["v1_available"] == 90.0

    def test_v2_only_items(self, db):
        """Materials only in v2 (no v1 match) appear in 'v2_only'."""
        mat, lot = _create_material_and_lot(db, name="OnlyInV2Material", code="MAT-V2ONLY-01", weight_kg=Decimal("750"))

        report = InventoryBridgeService.get_reconciliation_report(db)

        assert len(report["v2_only"]) >= 1
        v2_item = next((v for v in report["v2_only"] if v["v2_material_id"] == mat.id), None)
        assert v2_item is not None
        assert v2_item["v2_available_kg"] == 750.0

    def test_summary_counts(self, db):
        """Report includes summary counts."""
        report = InventoryBridgeService.get_reconciliation_report(db)

        assert "summary" in report
        assert "matched_count" in report["summary"]
        assert "drifted_count" in report["summary"]
        assert "v1_only_count" in report["summary"]
        assert "v2_only_count" in report["summary"]


# ===========================================================================
# Test feature flag
# ===========================================================================


class TestFeatureFlag:
    """Test that V2_BRIDGE_ENABLED controls bridge behavior."""

    def test_bridge_not_called_when_flag_off(self, db):
        """When V2_BRIDGE_ENABLED=false, advance_stage does NOT call bridge."""
        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        inv = create_test_inventory(db, name="Flag Test Steel", total=1000.0, used=0.0)

        item = create_test_production_item(
            db,
            customer.id,
            current_stage="fabrication",
            material_requirements=json.dumps([{"material_id": inv.id, "qty": 50, "inventory_name": inv.name}]),
        )
        st = StageTracking(
            production_item_id=item.id,
            stage="fabrication",
            status="in_progress",
            is_checked=True,
            started_at=datetime.utcnow(),
            updated_by=user.id,
        )
        db.add(st)
        db.commit()

        # Ensure flag is off
        with patch("backend_core.app.services.tracking_service.V2_BRIDGE_ENABLED", False):
            TrackingService.advance_stage(db, item.id, "painting", user.id)
            db.commit()

        # v1 deduction should happen
        db.refresh(inv)
        assert inv.used == 50.0

        # No v2 movement should exist
        count = db.query(StockMovement).filter(StockMovement.reference_type == "v1_bridge").count()
        assert count == 0

    def test_bridge_called_when_flag_on(self, db):
        """When V2_BRIDGE_ENABLED=true, advance_stage creates v2 movement."""
        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)

        mat, lot = _create_material_and_lot(db, name="Flag On Steel", code="MAT-FLAGON-01", weight_kg=Decimal("1000"))
        inv = create_test_inventory(db, name="Flag On Steel", total=1000.0, used=0.0)

        item = create_test_production_item(
            db,
            customer.id,
            current_stage="fabrication",
            material_requirements=json.dumps([{"material_id": inv.id, "qty": 75, "inventory_name": inv.name}]),
        )
        st = StageTracking(
            production_item_id=item.id,
            stage="fabrication",
            status="in_progress",
            is_checked=True,
            started_at=datetime.utcnow(),
            updated_by=user.id,
        )
        db.add(st)
        db.commit()

        with patch("backend_core.app.services.tracking_service.V2_BRIDGE_ENABLED", True):
            TrackingService.advance_stage(db, item.id, "painting", user.id)
            db.commit()

        # v1 deduction
        db.refresh(inv)
        assert inv.used == 75.0

        # v2 movement should exist
        movements = (
            db.query(StockMovement)
            .filter(
                StockMovement.reference_type == "v1_bridge",
            )
            .all()
        )
        assert len(movements) == 1
        assert float(movements[0].weight_change_kg) == -75.0
        assert movements[0].movement_type == MovementType.CONSUMPTION

        # Lot weight should be reduced
        db.refresh(lot)
        assert lot.current_weight_kg == Decimal("925")


# ===========================================================================
# Integration test: full advance_stage with bridge
# ===========================================================================


class TestIntegrationAdvanceStageWithBridge:
    """End-to-end test: advance_stage creates both v1 deduction and v2 movement."""

    def test_advance_stage_creates_both_v1_and_v2_records(self, db):
        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)

        mat, lot = _create_material_and_lot(db, name="Integration Steel", code="MAT-INT-01", weight_kg=Decimal("2000"))
        inv = create_test_inventory(db, name="Integration Steel", total=2000.0, used=0.0)

        item = create_test_production_item(
            db,
            customer.id,
            current_stage="fabrication",
            quantity=10.0,
            weight_per_unit=5.0,
            material_requirements=json.dumps([{"material_id": inv.id, "qty": 50, "inventory_name": inv.name}]),
        )
        st = StageTracking(
            production_item_id=item.id,
            stage="fabrication",
            status="in_progress",
            is_checked=True,
            started_at=datetime.utcnow(),
            updated_by=user.id,
        )
        db.add(st)
        db.commit()

        with patch("backend_core.app.services.tracking_service.V2_BRIDGE_ENABLED", True):
            result = TrackingService.advance_stage(db, item.id, "painting", user.id)
            db.commit()

        assert result["status"] == "updated"
        assert result["current_stage"] == "painting"

        # Verify v1 deduction
        db.refresh(inv)
        assert inv.used == 50.0

        # Verify MaterialUsage record
        usage = (
            db.query(MaterialUsage)
            .filter(
                MaterialUsage.production_item_id == item.id,
            )
            .first()
        )
        assert usage is not None
        assert usage.qty == 50.0

        # Verify v2 StockMovement
        v2_movement = (
            db.query(StockMovement)
            .filter(
                StockMovement.reference_type == "v1_bridge",
            )
            .first()
        )
        assert v2_movement is not None
        assert float(v2_movement.weight_change_kg) == -50.0

        # Verify lot weight updated
        db.refresh(lot)
        assert lot.current_weight_kg == Decimal("1950")

        # Verify item moved to painting
        db.refresh(item)
        assert item.current_stage == "painting"
        assert item.fabrication_deducted is True
