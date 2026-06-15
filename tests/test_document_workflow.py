"""
Tests for document workflow integration.

Covers:
- GRN transitions via workflow engine (draft->submitted->approved creates lots)
- GRN cancellation (draft->cancelled, submitted->cancelled)
- GRN invalid transitions (approved->submitted rejected)
- Dispatch transitions via workflow engine (draft->submitted->approved deducts stock)
- Role enforcement (only Boss/Admin can approve)
- transition_document() convenience function
"""

from datetime import datetime
from decimal import Decimal

import pytest

from backend_core.app.models_v2 import (
    DispatchLineItem,
    DispatchNote,
    DocumentStatus,
    GoodsReceiptNote,
    GRNLineItem,
    MaterialMaster,
    MaterialType,
    QAStatus,
    StorageLocation,
    Vendor,
    WeightUnit,
)
from backend_core.app.services.inventory_service import InvalidOperationError
from backend_core.app.services.workflow_engine import (
    WorkflowEngine,
    WorkflowError,
    get_dispatch_workflow,
    get_grn_workflow,
    register_document_hooks,
    transition_document,
)
from tests.conftest import create_test_stock_lot, create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_material(db, code="MAT-DW-01", name="HR Coil"):
    mat = MaterialMaster(code=code, name=name, material_type=MaterialType.COIL)
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


def _create_vendor(db, code="V-DW-01", name="Steel Corp"):
    vendor = Vendor(code=code, name=name)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def _create_location(db, code="WH-DW-01", name="Warehouse DW"):
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
    status=DocumentStatus.DRAFT,
):
    grn = GoodsReceiptNote(
        grn_number=f"GRN-DW-{datetime.utcnow().timestamp()}",
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


def _create_dispatch_with_line(db, customer_id, stock_lot_id, user_id, weight_kg=Decimal("100.000")):
    dispatch = DispatchNote(
        dispatch_number=f"DSP-DW-{datetime.utcnow().timestamp()}",
        customer_id=customer_id,
        status=DocumentStatus.DRAFT,
        created_by=user_id,
    )
    db.add(dispatch)
    db.flush()

    line = DispatchLineItem(
        dispatch_id=dispatch.id,
        stock_lot_id=stock_lot_id,
        dispatched_weight_kg=weight_kg,
    )
    db.add(line)
    db.commit()
    db.refresh(dispatch)
    return dispatch, line


# ===========================================================================
# TestGRNWorkflowDefinitions
# ===========================================================================


class TestGRNWorkflowDefinition:
    """Tests for get_grn_workflow() definition."""

    def test_grn_workflow_name(self):
        wf = get_grn_workflow()
        assert wf.name == "grn_workflow"

    def test_grn_workflow_has_four_states(self):
        wf = get_grn_workflow()
        assert len(wf.states) == 4
        state_names = [s.name for s in wf.states]
        assert state_names == ["draft", "submitted", "approved", "cancelled"]

    def test_grn_approved_state_has_hook(self):
        wf = get_grn_workflow()
        approved = wf.get_state("approved")
        assert "on_grn_approve" in approved.on_enter_hooks

    def test_grn_cancelled_state_has_hook(self):
        wf = get_grn_workflow()
        cancelled = wf.get_state("cancelled")
        assert "on_grn_cancel" in cancelled.on_enter_hooks


class TestDispatchWorkflowDefinition:
    """Tests for get_dispatch_workflow() definition."""

    def test_dispatch_workflow_name(self):
        wf = get_dispatch_workflow()
        assert wf.name == "dispatch_workflow"

    def test_dispatch_approved_state_has_hook(self):
        wf = get_dispatch_workflow()
        approved = wf.get_state("approved")
        assert "on_dispatch_approve" in approved.on_enter_hooks

    def test_dispatch_cancelled_state_has_hook(self):
        wf = get_dispatch_workflow()
        cancelled = wf.get_state("cancelled")
        assert "on_dispatch_cancel" in cancelled.on_enter_hooks


# ===========================================================================
# TestGRNTransitions
# ===========================================================================


class TestGRNTransitions:
    """Test GRN document transitions through the workflow engine."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()
        # Reset the registration flag so hooks can be re-registered
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def teardown_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def test_grn_draft_to_submitted(self, db):
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-01")
        mat = _create_material(db, code="MAT-TR-01")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.DRAFT,
        )

        result = transition_document(db, grn, "submitted", "Boss")

        assert result.success is True
        assert result.from_state == "draft"
        assert result.to_state == "submitted"
        assert grn.status == DocumentStatus.SUBMITTED

    def test_grn_submitted_to_approved_creates_lots(self, db):
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-02")
        mat = _create_material(db, code="MAT-TR-02")
        loc = _create_location(db, code="WH-TR-01")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            weight_kg=Decimal("500.000"),
            qa_status=QAStatus.APPROVED,
            status=DocumentStatus.SUBMITTED,
        )

        context = {
            "grn_id": grn.id,
            "user_id": user.id,
            "location_id": loc.id,
        }
        result = transition_document(db, grn, "approved", "Boss", context)
        db.commit()

        assert result.success is True
        assert grn.status == DocumentStatus.APPROVED
        assert "on_grn_approve" in result.hooks_executed

        # Verify lots were created
        lots = context.get("created_lots", [])
        assert len(lots) == 1
        assert lots[0].current_weight_kg == Decimal("500.000")
        assert lots[0].material_id == mat.id

    def test_grn_full_workflow_draft_to_approved(self, db):
        """Full path: draft -> submitted -> approved with lot creation."""
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-03")
        mat = _create_material(db, code="MAT-TR-03")
        loc = _create_location(db, code="WH-TR-02")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            weight_kg=Decimal("750.000"),
            qa_status=QAStatus.APPROVED,
            status=DocumentStatus.DRAFT,
        )

        # Step 1: draft -> submitted
        r1 = transition_document(db, grn, "submitted", "Boss")
        assert r1.success
        assert grn.status == DocumentStatus.SUBMITTED

        # Step 2: submitted -> approved
        context = {"grn_id": grn.id, "user_id": user.id, "location_id": loc.id}
        r2 = transition_document(db, grn, "approved", "Boss", context)
        db.commit()
        assert r2.success
        assert grn.status == DocumentStatus.APPROVED

        lots = context["created_lots"]
        assert len(lots) == 1
        assert lots[0].current_weight_kg == Decimal("750.000")

    def test_grn_draft_to_cancelled(self, db):
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-04")
        mat = _create_material(db, code="MAT-TR-04")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.DRAFT,
        )

        context = {"grn_id": grn.id, "reason": "Not needed"}
        result = transition_document(db, grn, "cancelled", "Boss", context)

        assert result.success is True
        assert grn.status == DocumentStatus.CANCELLED
        assert "on_grn_cancel" in result.hooks_executed

    def test_grn_submitted_to_cancelled(self, db):
        user = create_test_user(db, role="Admin")
        vendor = _create_vendor(db, code="V-TR-05")
        mat = _create_material(db, code="MAT-TR-05")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.SUBMITTED,
        )

        context = {"grn_id": grn.id, "reason": "Vendor issue"}
        result = transition_document(db, grn, "cancelled", "Admin", context)

        assert result.success is True
        assert grn.status == DocumentStatus.CANCELLED

    def test_grn_approved_to_submitted_rejected(self, db):
        """Once approved, cannot go back to submitted."""
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-06")
        mat = _create_material(db, code="MAT-TR-06")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.APPROVED,
        )

        with pytest.raises(WorkflowError, match="No transition"):
            transition_document(db, grn, "submitted", "Boss")

    def test_grn_approved_to_cancelled_rejected(self, db):
        """Once approved, cannot be cancelled."""
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-07")
        mat = _create_material(db, code="MAT-TR-07")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.APPROVED,
        )

        with pytest.raises(WorkflowError, match="No transition"):
            transition_document(db, grn, "cancelled", "Boss")

    def test_grn_approve_pending_qa_rejected(self, db):
        """Approval with pending QA items should fail via hook."""
        user = create_test_user(db, role="Boss")
        vendor = _create_vendor(db, code="V-TR-08")
        mat = _create_material(db, code="MAT-TR-08")
        loc = _create_location(db, code="WH-TR-03")

        grn, line = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            qa_status=QAStatus.PENDING,
            status=DocumentStatus.SUBMITTED,
        )

        context = {"grn_id": grn.id, "user_id": user.id, "location_id": loc.id}
        with pytest.raises(InvalidOperationError, match="pending QA"):
            transition_document(db, grn, "approved", "Boss", context)


# ===========================================================================
# TestDispatchTransitions
# ===========================================================================


class TestDispatchTransitions:
    """Test dispatch document transitions through the workflow engine."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def teardown_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def test_dispatch_draft_to_submitted(self, db):
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        lot = create_test_stock_lot(db, current_weight_kg=Decimal("500.000"))

        dispatch, line = _create_dispatch_with_line(db, customer.id, lot.id, user.id, weight_kg=Decimal("100.000"))

        result = transition_document(db, dispatch, "submitted", "Boss")

        assert result.success is True
        assert dispatch.status == DocumentStatus.SUBMITTED

    def test_dispatch_full_workflow_deducts_stock(self, db):
        """Full path: draft -> submitted -> approved with stock deduction."""
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("500.000"),
            current_weight_kg=Decimal("500.000"),
        )

        dispatch, line = _create_dispatch_with_line(db, customer.id, lot.id, user.id, weight_kg=Decimal("200.000"))

        # Step 1: draft -> submitted
        r1 = transition_document(db, dispatch, "submitted", "Boss")
        assert r1.success

        # Step 2: submitted -> approved
        context = {"dispatch_id": dispatch.id, "user_id": user.id}
        r2 = transition_document(db, dispatch, "approved", "Boss", context)
        db.commit()

        assert r2.success
        assert dispatch.status == DocumentStatus.APPROVED
        assert "on_dispatch_approve" in r2.hooks_executed

        # Verify stock was deducted
        movements = context.get("movements", [])
        assert len(movements) == 1
        assert movements[0]["weight_dispatched"] == 200.0

        # Verify lot weight reduced
        db.refresh(lot)
        assert lot.current_weight_kg == Decimal("300.000")

    def test_dispatch_draft_to_cancelled(self, db):
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        lot = create_test_stock_lot(db)

        dispatch, line = _create_dispatch_with_line(db, customer.id, lot.id, user.id)

        context = {"dispatch_id": dispatch.id, "reason": "Customer cancelled"}
        result = transition_document(db, dispatch, "cancelled", "Boss", context)

        assert result.success is True
        assert dispatch.status == DocumentStatus.CANCELLED
        assert "on_dispatch_cancel" in result.hooks_executed

    def test_dispatch_approved_to_submitted_rejected(self, db):
        """Cannot go from approved back to submitted."""
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)

        dispatch = DispatchNote(
            dispatch_number=f"DSP-REJ-{datetime.utcnow().timestamp()}",
            customer_id=customer.id,
            status=DocumentStatus.APPROVED,
            created_by=user.id,
        )
        db.add(dispatch)
        db.commit()

        with pytest.raises(WorkflowError, match="No transition"):
            transition_document(db, dispatch, "submitted", "Boss")


# ===========================================================================
# TestRoleEnforcement
# ===========================================================================


class TestRoleEnforcement:
    """Test that role restrictions are enforced by the workflow engine."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def teardown_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def test_user_role_cannot_approve_grn(self, db):
        user = create_test_user(db, role="User")
        vendor = _create_vendor(db, code="V-ROLE-01")
        mat = _create_material(db, code="MAT-ROLE-01")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.SUBMITTED,
        )

        with pytest.raises(WorkflowError, match="not allowed"):
            transition_document(db, grn, "approved", "User")

    def test_user_role_cannot_cancel_grn(self, db):
        user = create_test_user(db, role="User")
        vendor = _create_vendor(db, code="V-ROLE-02")
        mat = _create_material(db, code="MAT-ROLE-02")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.DRAFT,
        )

        with pytest.raises(WorkflowError, match="not allowed"):
            transition_document(db, grn, "cancelled", "User")

    def test_user_role_can_submit_grn(self, db):
        user = create_test_user(db, role="User")
        vendor = _create_vendor(db, code="V-ROLE-03")
        mat = _create_material(db, code="MAT-ROLE-03")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            status=DocumentStatus.DRAFT,
        )

        result = transition_document(db, grn, "submitted", "User")
        assert result.success is True

    def test_storekeeper_cannot_approve_dispatch(self, db):
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Store Keeper")
        customer = create_test_customer(db)

        dispatch = DispatchNote(
            dispatch_number=f"DSP-ROLE-{datetime.utcnow().timestamp()}",
            customer_id=customer.id,
            status=DocumentStatus.SUBMITTED,
            created_by=user.id,
        )
        db.add(dispatch)
        db.commit()

        with pytest.raises(WorkflowError, match="not allowed"):
            transition_document(db, dispatch, "approved", "Store Keeper")

    def test_boss_can_approve_dispatch(self, db):
        from tests.conftest import create_test_customer

        user = create_test_user(db, role="Boss")
        customer = create_test_customer(db)
        lot = create_test_stock_lot(
            db,
            net_weight_kg=Decimal("500.000"),
            current_weight_kg=Decimal("500.000"),
        )

        dispatch, line = _create_dispatch_with_line(db, customer.id, lot.id, user.id, weight_kg=Decimal("100.000"))
        dispatch.status = DocumentStatus.SUBMITTED
        db.commit()

        context = {"dispatch_id": dispatch.id, "user_id": user.id}
        result = transition_document(db, dispatch, "approved", "Boss", context)
        db.commit()

        assert result.success is True
        assert dispatch.status == DocumentStatus.APPROVED

    def test_admin_can_approve(self, db):
        user = create_test_user(db, role="Admin")
        vendor = _create_vendor(db, code="V-ROLE-04")
        mat = _create_material(db, code="MAT-ROLE-04")
        loc = _create_location(db, code="WH-ROLE-01")

        grn, _ = _create_grn_with_line(
            db,
            vendor.id,
            mat.id,
            user.id,
            qa_status=QAStatus.APPROVED,
            status=DocumentStatus.SUBMITTED,
        )

        context = {"grn_id": grn.id, "user_id": user.id, "location_id": loc.id}
        result = transition_document(db, grn, "approved", "Admin", context)
        db.commit()

        assert result.success is True
        assert grn.status == DocumentStatus.APPROVED


# ===========================================================================
# TestHookRegistration
# ===========================================================================


class TestDocumentHookRegistration:
    """Test that register_document_hooks() properly registers all hooks."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def teardown_method(self):
        WorkflowEngine.clear_hooks()
        import backend_core.app.services.workflow_engine as wf_mod

        wf_mod._document_hooks_registered = False

    def test_register_document_hooks_registers_all(self):
        register_document_hooks()
        assert "on_grn_approve" in WorkflowEngine._hooks
        assert "on_grn_cancel" in WorkflowEngine._hooks
        assert "on_dispatch_approve" in WorkflowEngine._hooks
        assert "on_dispatch_cancel" in WorkflowEngine._hooks

    def test_register_document_hooks_idempotent(self):
        register_document_hooks()
        first_approve = WorkflowEngine._hooks["on_grn_approve"]
        register_document_hooks()
        # Same function reference — not re-registered
        assert WorkflowEngine._hooks["on_grn_approve"] is first_approve
