"""
Unit tests for TrackingService — stage advancement, material deduction,
split_item, and checklist toggling.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

import backend_core.app.services.tracking_service as tracking_module
from backend_core.app.models import (
    MaterialUsage,
    Notification,
    ProductionItem,
    StageTracking,
)
from backend_core.app.services.tracking_service import STAGE_FLOW, TrackingService

# Reuse conftest helpers
from tests.conftest import (
    create_test_customer,
    create_test_inventory,
    create_test_production_item,
    create_test_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_item_at_stage(db, stage="fabrication", checklist_checked=False, **item_overrides):
    """Create a customer + production item + stage tracking row."""
    user = create_test_user(db, role="Boss")
    customer = create_test_customer(db)
    item = create_test_production_item(db, customer.id, current_stage=stage, **item_overrides)

    # Create stage tracking row for the current stage
    st = StageTracking(
        production_item_id=item.id,
        stage=stage,
        status="in_progress",
        is_checked=checklist_checked,
        started_at=datetime.utcnow(),
        updated_by=user.id,
    )
    db.add(st)
    db.commit()
    db.refresh(item)
    return user, customer, item


# ===========================================================================
# TestAdvanceStage
# ===========================================================================


class TestAdvanceStage:
    """Tests for TrackingService.advance_stage()"""

    def test_advance_fabrication_to_painting_succeeds(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        result = TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        assert result["status"] == "updated"
        assert result["current_stage"] == "painting"

        db.refresh(item)
        assert item.current_stage == "painting"

    def test_advance_painting_to_dispatch_succeeds(self, db):
        user, customer, item = _setup_item_at_stage(db, "painting", checklist_checked=True)

        result = TrackingService.advance_stage(db, item.id, "dispatch", user.id)
        db.commit()

        assert result["current_stage"] == "dispatch"

    def test_advance_dispatch_to_completed_succeeds(self, db):
        user, customer, item = _setup_item_at_stage(db, "dispatch", checklist_checked=True)

        TrackingService.advance_stage(db, item.id, "completed", user.id)
        db.commit()

        db.refresh(item)
        assert item.current_stage == "completed"
        assert item.is_completed is True

    def test_full_stage_flow_fabrication_through_completed(self, db):
        """Walk through every stage in sequence."""
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        for target in ["painting", "dispatch", "completed"]:
            TrackingService.advance_stage(db, item.id, target, user.id)
            db.commit()
            db.refresh(item)
            assert item.current_stage == target

            # Set checklist for next stage if not completed
            if target != "completed":
                st = db.query(StageTracking).filter_by(production_item_id=item.id, stage=target).first()
                st.is_checked = True
                db.commit()

    def test_stage_skip_fabrication_to_dispatch_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with pytest.raises(ValueError, match="Stage must advance to 'painting'"):
            TrackingService.advance_stage(db, item.id, "dispatch", user.id)

    def test_stage_skip_fabrication_to_completed_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with pytest.raises(ValueError, match="Stage must advance to 'painting'"):
            TrackingService.advance_stage(db, item.id, "completed", user.id)

    def test_advance_without_checklist_raises_error(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=False)

        with pytest.raises(ValueError, match="Checklist must be completed"):
            TrackingService.advance_stage(db, item.id, "painting", user.id)

    def test_advance_nonexistent_item_raises_error(self, db):
        user = create_test_user(db, role="Boss")
        with pytest.raises(ValueError, match="Production item not found"):
            TrackingService.advance_stage(db, 99999, "painting", user.id)

    def test_advance_from_completed_raises_error(self, db):
        """completed has no next stage, so any advance should fail."""
        user, customer, item = _setup_item_at_stage(db, "completed", checklist_checked=True)

        with pytest.raises(ValueError):
            TrackingService.advance_stage(db, item.id, "fabrication", user.id)

    def test_advance_marks_current_stage_completed(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        fab_stage = db.query(StageTracking).filter_by(production_item_id=item.id, stage="fabrication").first()
        assert fab_stage.status == "completed"
        assert fab_stage.completed_at is not None

    def test_advance_creates_next_stage_row(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        painting_stage = db.query(StageTracking).filter_by(production_item_id=item.id, stage="painting").first()
        assert painting_stage is not None
        assert painting_stage.status == "in_progress"


# ===========================================================================
# TestMaterialDeduction
# ===========================================================================


class TestMaterialDeduction:
    """Tests for _deduct_materials_for_fabrication and double-deduction prevention."""

    def test_deduction_fires_on_fabrication_to_painting(self, db):
        """When advancing from fabrication to painting, material deduction should fire."""
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="ISMC 200",
            weight_per_unit=50.0,
            quantity=2.0,
        )

        TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        db.refresh(item)
        assert item.fabrication_deducted is True

        db.refresh(inv)
        assert inv.used == 100.0  # 50 * 2

    def test_double_deduction_prevention(self, db):
        """Calling _deduct_materials_for_fabrication a second time should be a no-op."""
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="ISMC 200",
            weight_per_unit=50.0,
            quantity=2.0,
        )

        # First deduction
        result1 = TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()
        assert result1["success"] is True

        # Second deduction should be skipped
        result2 = TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()
        assert result2["skipped_reason"] == "Already deducted"

        db.refresh(inv)
        assert inv.used == 100.0  # Not 200

    def test_deduction_with_explicit_material_requirements_json(self, db):
        """Material requirements stored as JSON should be used for deduction."""
        inv = create_test_inventory(db, name="Custom Mat", total=500.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
        )

        # Set explicit material requirements
        item.material_requirements = json.dumps([{"material_id": inv.id, "qty": 75.5, "inventory_name": inv.name}])
        db.commit()

        result = TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()

        assert result["success"] is True
        assert len(result["deducted"]) == 1
        assert result["deducted"][0]["qty"] == 75.5

        db.refresh(inv)
        assert inv.used == 75.5

    def test_deduction_no_material_match_creates_notification(self, db):
        """When no material match found, a notification should be created."""
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="NONEXISTENT MATERIAL",
            weight_per_unit=10.0,
            quantity=1.0,
        )

        result = TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()

        assert result["skipped_reason"] is not None
        assert item.fabrication_deducted is True  # Still marked to prevent retry

        # Check notification was created
        notif = db.query(Notification).filter(Notification.category == "low_inventory").first()
        assert notif is not None

    def test_deduction_creates_material_usage_record(self, db):
        _inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="ISMC 200",
            weight_per_unit=30.0,
            quantity=1.0,
        )

        TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()

        usage = db.query(MaterialUsage).filter_by(production_item_id=item.id).first()
        assert usage is not None
        assert usage.qty == 30.0

    def test_deduction_low_stock_warning(self, db):
        """When available stock is less than needed, a warning should be added."""
        _inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=10.0, used=5.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="ISMC 200",
            weight_per_unit=20.0,
            quantity=1.0,
        )

        result = TrackingService._deduct_materials_for_fabrication(item, db, user.id)
        db.commit()

        assert any("Low stock" in w for w in result["warnings"])

    def test_painting_to_dispatch_does_not_rededuect(self, db):
        """Advancing from painting to dispatch should NOT trigger material deduction again."""
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=100.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "painting",
            checklist_checked=True,
        )
        item.fabrication_deducted = True  # Already deducted
        db.commit()

        TrackingService.advance_stage(db, item.id, "dispatch", user.id)
        db.commit()

        db.refresh(inv)
        assert inv.used == 100.0  # Unchanged


# ===========================================================================
# TestSplitItem
# ===========================================================================


class TestSplitItem:
    """Tests for TrackingService.split_item()"""

    def test_split_reduces_original_and_creates_new(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True, quantity=10.0)

        result = TrackingService.split_item(db, item.id, 3.0)
        db.commit()

        assert result["remaining_quantity"] == 7.0
        assert result["moved_quantity"] == 3.0

        new_item = db.query(ProductionItem).filter_by(id=result["new_item_id"]).first()
        assert new_item is not None
        assert new_item.quantity == 3.0
        assert new_item.parent_item_id == item.id

    def test_split_clones_stage_tracking(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True, quantity=10.0)

        result = TrackingService.split_item(db, item.id, 4.0)
        db.commit()

        new_stages = db.query(StageTracking).filter_by(production_item_id=result["new_item_id"]).all()

        stage_names = {s.stage for s in new_stages}
        assert "fabrication" in stage_names
        assert "painting" in stage_names
        assert "dispatch" in stage_names

    def test_split_zero_quantity_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", quantity=10.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            TrackingService.split_item(db, item.id, 0.0)

    def test_split_negative_quantity_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", quantity=10.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            TrackingService.split_item(db, item.id, -5.0)

    def test_split_full_quantity_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", quantity=10.0)

        with pytest.raises(ValueError, match="Move quantity must be less than existing quantity"):
            TrackingService.split_item(db, item.id, 10.0)

    def test_split_over_quantity_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", quantity=10.0)

        with pytest.raises(ValueError, match="Move quantity must be less than existing quantity"):
            TrackingService.split_item(db, item.id, 15.0)

    def test_split_completed_item_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", quantity=10.0)
        item.is_completed = True
        db.commit()

        with pytest.raises(ValueError, match="Cannot split a completed item"):
            TrackingService.split_item(db, item.id, 3.0)

    def test_split_preserves_item_code_and_name(self, db):
        user, customer, item = _setup_item_at_stage(
            db, "fabrication", quantity=10.0, item_code="DWG-001", item_name="Beam Assembly"
        )

        result = TrackingService.split_item(db, item.id, 4.0)
        db.commit()

        new_item = db.query(ProductionItem).filter_by(id=result["new_item_id"]).first()
        assert new_item.item_code == "DWG-001"
        assert new_item.item_name == "Beam Assembly"

    def test_split_inherits_deduction_flags(self, db):
        user, customer, item = _setup_item_at_stage(db, "painting", quantity=10.0, checklist_checked=True)
        item.fabrication_deducted = True
        item.material_deducted = True
        db.commit()

        result = TrackingService.split_item(db, item.id, 3.0)
        db.commit()

        new_item = db.query(ProductionItem).filter_by(id=result["new_item_id"]).first()
        assert new_item.fabrication_deducted is True
        assert new_item.material_deducted is True

    def test_split_nonexistent_item_raises_error(self, db):
        with pytest.raises(ValueError, match="Production item not found"):
            TrackingService.split_item(db, 99999, 5.0)

    def test_split_with_material_requirements_divides_correctly(self, db):
        """Regression: split_item must parse material_requirements JSON without NameError.

        Before the fix, `json` was only imported inside _deduct_materials_for_fabrication,
        so split_item would raise NameError (silently caught by bare except).
        """
        inv = create_test_inventory(db, name="Steel Beam", total=1000.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            quantity=10.0,
        )
        # Set explicit material requirements JSON
        item.material_requirements = json.dumps([{"material_id": inv.id, "qty": 100.0, "inventory_name": inv.name}])
        db.commit()

        result = TrackingService.split_item(db, item.id, 4.0)
        db.commit()

        # Original item should have 60% of material (6/10 * 100 = 60)
        db.refresh(item)
        original_reqs = json.loads(item.material_requirements)
        assert len(original_reqs) == 1
        assert abs(original_reqs[0]["qty"] - 60.0) < 0.01

        # New item should have 40% of material (4/10 * 100 = 40)
        new_item = db.query(ProductionItem).filter_by(id=result["new_item_id"]).first()
        new_reqs = json.loads(new_item.material_requirements)
        assert len(new_reqs) == 1
        assert abs(new_reqs[0]["qty"] - 40.0) < 0.01


# ===========================================================================
# TestToggleChecklist
# ===========================================================================


class TestToggleChecklist:
    """Tests for TrackingService.toggle_checklist()"""

    def test_toggle_checklist_to_checked(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=False)

        result = TrackingService.toggle_checklist(db, item.id, True, user.id)
        db.commit()

        assert result is True
        st = db.query(StageTracking).filter_by(production_item_id=item.id, stage="fabrication").first()
        assert st.is_checked is True

    def test_toggle_checklist_to_unchecked(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        TrackingService.toggle_checklist(db, item.id, False, user.id)
        db.commit()

        st = db.query(StageTracking).filter_by(production_item_id=item.id, stage="fabrication").first()
        assert st.is_checked is False

    def test_toggle_checklist_creates_stage_row_if_missing(self, db):
        """If no StageTracking row exists for the current stage, one is created."""
        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        item = create_test_production_item(db, customer.id, current_stage="fabrication")
        # No StageTracking row created intentionally

        result = TrackingService.toggle_checklist(db, item.id, True, user.id)
        db.commit()

        assert result is True
        st = db.query(StageTracking).filter_by(production_item_id=item.id, stage="fabrication").first()
        assert st is not None
        assert st.is_checked is True

    def test_toggle_checklist_nonexistent_item_raises_error(self, db):
        with pytest.raises(ValueError, match="Production item not found"):
            TrackingService.toggle_checklist(db, 99999, True, 1)


# ===========================================================================
# TestPartialMoveViaAdvanceStage
# ===========================================================================


class TestPartialMoveViaAdvanceStage:
    """Tests for partial quantity move through advance_stage with move_quantity."""

    def test_advance_with_partial_quantity_splits_and_advances_new_item(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True, quantity=10.0)

        result = TrackingService.advance_stage(db, item.id, "painting", user.id, move_quantity=4.0)
        db.commit()

        # The advanced item should be a new item (the split child)
        assert result["item_id"] != item.id
        assert result["current_stage"] == "painting"

        # Original item should still be in fabrication with reduced qty
        db.refresh(item)
        assert item.current_stage == "fabrication"
        assert item.quantity == 6.0


# ===========================================================================
# TestStageFlowConstants
# ===========================================================================


class TestStageFlowConstants:
    """Validate STAGE_FLOW dict integrity."""

    def test_stage_flow_contains_all_stages(self):
        assert "fabrication" in STAGE_FLOW
        assert "painting" in STAGE_FLOW
        assert "dispatch" in STAGE_FLOW
        assert "completed" in STAGE_FLOW

    def test_completed_has_no_next_stage(self):
        assert STAGE_FLOW["completed"] is None

    def test_stage_flow_is_sequential(self):
        assert STAGE_FLOW["fabrication"] == "painting"
        assert STAGE_FLOW["painting"] == "dispatch"
        assert STAGE_FLOW["dispatch"] == "completed"


# ===========================================================================
# TestWorkflowEngineIntegration
# ===========================================================================


class TestWorkflowEngineIntegration:
    """Tests for advance_stage when USE_WORKFLOW_ENGINE=true.

    These mirror the core TestAdvanceStage and TestMaterialDeduction tests
    to verify identical behaviour when the workflow engine path is active.
    """

    def setup_method(self):
        from backend_core.app.services.workflow_engine import WorkflowEngine

        WorkflowEngine.clear_hooks()
        # Reset the hook registration flag so hooks are re-registered each test
        tracking_module._tracking_hooks_registered = False

    def teardown_method(self):
        from backend_core.app.services.workflow_engine import WorkflowEngine

        WorkflowEngine.clear_hooks()
        tracking_module._tracking_hooks_registered = False

    # -- Basic stage advancement -------------------------------------------

    def test_engine_advance_fabrication_to_painting(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            result = TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        assert result["status"] == "updated"
        assert result["current_stage"] == "painting"

        db.refresh(item)
        assert item.current_stage == "painting"

    def test_engine_advance_painting_to_dispatch(self, db):
        user, customer, item = _setup_item_at_stage(db, "painting", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            result = TrackingService.advance_stage(db, item.id, "dispatch", user.id)
        db.commit()

        assert result["current_stage"] == "dispatch"

    def test_engine_advance_dispatch_to_completed(self, db):
        user, customer, item = _setup_item_at_stage(db, "dispatch", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            TrackingService.advance_stage(db, item.id, "completed", user.id)
        db.commit()

        db.refresh(item)
        assert item.current_stage == "completed"
        assert item.is_completed is True

    def test_engine_full_stage_flow(self, db):
        """Walk through every stage in sequence via the engine."""
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            for target in ["painting", "dispatch", "completed"]:
                TrackingService.advance_stage(db, item.id, target, user.id)
                db.commit()
                db.refresh(item)
                assert item.current_stage == target

                if target != "completed":
                    st = db.query(StageTracking).filter_by(production_item_id=item.id, stage=target).first()
                    st.is_checked = True
                    db.commit()

    # -- Invalid transitions -----------------------------------------------

    def test_engine_skip_fabrication_to_dispatch_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            with pytest.raises(ValueError, match="Stage must advance to 'painting'"):
                TrackingService.advance_stage(db, item.id, "dispatch", user.id)

    def test_engine_skip_fabrication_to_completed_rejected(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            with pytest.raises(ValueError, match="Stage must advance to 'painting'"):
                TrackingService.advance_stage(db, item.id, "completed", user.id)

    def test_engine_advance_without_checklist_raises_error(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=False)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            with pytest.raises(ValueError, match="Checklist must be completed"):
                TrackingService.advance_stage(db, item.id, "painting", user.id)

    def test_engine_advance_nonexistent_item_raises_error(self, db):
        user = create_test_user(db, role="Boss")

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            with pytest.raises(ValueError, match="Production item not found"):
                TrackingService.advance_stage(db, 99999, "painting", user.id)

    # -- Material deduction via hook ---------------------------------------

    def test_engine_deduction_fires_on_fabrication_to_painting(self, db):
        """Material deduction hook should fire when leaving fabrication."""
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=0.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "fabrication",
            checklist_checked=True,
            section="ISMC 200",
            weight_per_unit=50.0,
            quantity=2.0,
        )

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        db.refresh(item)
        assert item.fabrication_deducted is True

        db.refresh(inv)
        assert inv.used == 100.0  # 50 * 2

    def test_engine_painting_to_dispatch_no_rededuection(self, db):
        """Advancing painting->dispatch should NOT re-trigger material deduction."""
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200", total=1000.0, used=100.0)
        user, customer, item = _setup_item_at_stage(
            db,
            "painting",
            checklist_checked=True,
        )
        item.fabrication_deducted = True
        db.commit()

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            TrackingService.advance_stage(db, item.id, "dispatch", user.id)
        db.commit()

        db.refresh(inv)
        assert inv.used == 100.0  # Unchanged

    # -- Stage tracking rows -----------------------------------------------

    def test_engine_marks_current_stage_completed(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        fab_stage = db.query(StageTracking).filter_by(production_item_id=item.id, stage="fabrication").first()
        assert fab_stage.status == "completed"
        assert fab_stage.completed_at is not None

    def test_engine_creates_next_stage_row(self, db):
        user, customer, item = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            TrackingService.advance_stage(db, item.id, "painting", user.id)
        db.commit()

        painting_stage = db.query(StageTracking).filter_by(production_item_id=item.id, stage="painting").first()
        assert painting_stage is not None
        assert painting_stage.status == "in_progress"

    # -- Parity check: same result shape with flag on vs off ---------------

    def test_engine_vs_legacy_same_result_shape(self, db):
        """Both paths must return the same dict keys."""
        user1, customer1, item1 = _setup_item_at_stage(db, "fabrication", checklist_checked=True)
        user2, customer2, item2 = _setup_item_at_stage(db, "fabrication", checklist_checked=True)

        legacy_result = TrackingService._advance_stage_legacy(db, item1.id, "painting", user1.id)
        db.commit()

        # Reset hook flag for engine path
        tracking_module._tracking_hooks_registered = False
        with patch.object(tracking_module, "USE_WORKFLOW_ENGINE", True):
            engine_result = TrackingService._advance_stage_via_engine(db, item2.id, "painting", user2.id)
        db.commit()

        assert set(legacy_result.keys()) == set(engine_result.keys())
        assert legacy_result["status"] == engine_result["status"]
        assert legacy_result["current_stage"] == engine_result["current_stage"]
