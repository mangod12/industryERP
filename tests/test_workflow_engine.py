"""
Tests for the configurable workflow engine.

Covers:
- WorkflowDefinition validation (duplicates, empty, bad transitions)
- Transition validation (allowed, denied, unknown states)
- Transition execution (hooks, ordering, context, errors)
- Query helpers (allowed transitions, next state)
- Built-in workflows (v1 production, v3 production, document)
- Hook registry (register, execute, missing)
- DB loading (from StageConfig, fallback)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure imports work regardless of cwd
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend_core.app.services.workflow_engine import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowError,
    WorkflowState,
    WorkflowTransition,
    WorkflowTransitionResult,
    get_document_workflow,
    get_production_workflow_v1,
    get_production_workflow_v3,
    load_workflow_from_db,
)

# =============================================================================
# Helpers
# =============================================================================


def _linear_workflow(name: str = "test_wf") -> WorkflowDefinition:
    """A simple A -> B -> C linear workflow for testing."""
    states = (
        WorkflowState(name="A", sequence=1, allowed_roles=("Boss", "User")),
        WorkflowState(name="B", sequence=2, allowed_roles=("Boss", "User")),
        WorkflowState(name="C", sequence=3, allowed_roles=("Boss",)),
    )
    transitions = (
        WorkflowTransition(from_state="A", to_state="B", allowed_roles=("Boss", "User")),
        WorkflowTransition(from_state="B", to_state="C", allowed_roles=("Boss",)),
    )
    return WorkflowDefinition(name=name, states=states, transitions=transitions)


def _make_db():
    """Return a mock Session for hook tests."""
    return MagicMock()


# =============================================================================
# TestWorkflowDefinition
# =============================================================================


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition construction and validation."""

    def test_valid_workflow_creation(self):
        wf = _linear_workflow()
        assert wf.name == "test_wf"
        assert len(wf.states) == 3
        assert len(wf.transitions) == 2

    def test_duplicate_state_names_rejected(self):
        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="A", sequence=2),
        )
        with pytest.raises(WorkflowError, match="Duplicate state names"):
            WorkflowDefinition(name="bad", states=states, transitions=())

    def test_empty_workflow_rejected(self):
        with pytest.raises(WorkflowError, match="at least one state"):
            WorkflowDefinition(name="empty", states=(), transitions=())

    def test_transition_referencing_unknown_from_state(self):
        states = (WorkflowState(name="A", sequence=1),)
        transitions = (WorkflowTransition(from_state="X", to_state="A"),)
        with pytest.raises(WorkflowError, match="unknown from_state 'X'"):
            WorkflowDefinition(name="bad", states=states, transitions=transitions)

    def test_transition_referencing_unknown_to_state(self):
        states = (WorkflowState(name="A", sequence=1),)
        transitions = (WorkflowTransition(from_state="A", to_state="Z"),)
        with pytest.raises(WorkflowError, match="unknown to_state 'Z'"):
            WorkflowDefinition(name="bad", states=states, transitions=transitions)

    def test_get_state_found(self):
        wf = _linear_workflow()
        assert wf.get_state("B") is not None
        assert wf.get_state("B").sequence == 2

    def test_get_state_not_found(self):
        wf = _linear_workflow()
        assert wf.get_state("Z") is None

    def test_single_state_workflow(self):
        """A workflow with one state and no transitions is valid."""
        wf = WorkflowDefinition(
            name="single",
            states=(WorkflowState(name="only", sequence=1),),
            transitions=(),
        )
        assert len(wf.states) == 1


# =============================================================================
# TestValidateTransition
# =============================================================================


class TestValidateTransition:
    """Tests for WorkflowEngine.validate_transition."""

    def test_valid_transition_allowed(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.validate_transition("A", "B", "Boss") is True

    def test_invalid_skip_rejected(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.validate_transition("A", "C", "Boss") is False

    def test_role_check_enforced(self):
        engine = WorkflowEngine(_linear_workflow())
        # B->C only allowed for Boss
        assert engine.validate_transition("B", "C", "User") is False
        assert engine.validate_transition("B", "C", "Boss") is True

    def test_unknown_current_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.validate_transition("X", "A", "Boss") is False

    def test_unknown_target_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.validate_transition("A", "X", "Boss") is False

    def test_transition_with_no_role_restriction(self):
        """Transitions with empty allowed_roles should be open to all."""
        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="B", sequence=2),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B", allowed_roles=()),)
        wf = WorkflowDefinition(name="open", states=states, transitions=transitions)
        engine = WorkflowEngine(wf)
        assert engine.validate_transition("A", "B", "AnyRole") is True


# =============================================================================
# TestExecuteTransition
# =============================================================================


class TestExecuteTransition:
    """Tests for WorkflowEngine.execute_transition."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()

    def teardown_method(self):
        WorkflowEngine.clear_hooks()

    def test_happy_path_with_hooks(self):
        call_log: list[str] = []

        WorkflowEngine.register_hook("exit_A", lambda db, ctx: call_log.append("exit_A"))
        WorkflowEngine.register_hook("enter_B", lambda db, ctx: call_log.append("enter_B"))

        states = (
            WorkflowState(name="A", sequence=1, on_exit_hooks=("exit_A",)),
            WorkflowState(name="B", sequence=2, on_enter_hooks=("enter_B",)),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="hook_test", states=states, transitions=transitions)

        engine = WorkflowEngine(wf)
        result = engine.execute_transition(_make_db(), "A", "B", "Boss")

        assert result.success is True
        assert result.from_state == "A"
        assert result.to_state == "B"
        assert result.hooks_executed == ("exit_A", "enter_B")

    def test_hook_execution_order_exit_before_enter(self):
        order: list[str] = []

        WorkflowEngine.register_hook("on_exit", lambda db, ctx: order.append("exit"))
        WorkflowEngine.register_hook("on_enter", lambda db, ctx: order.append("enter"))

        states = (
            WorkflowState(name="A", sequence=1, on_exit_hooks=("on_exit",)),
            WorkflowState(name="B", sequence=2, on_enter_hooks=("on_enter",)),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="order_test", states=states, transitions=transitions)

        WorkflowEngine(wf).execute_transition(_make_db(), "A", "B", "Boss")
        assert order == ["exit", "enter"]

    def test_failed_hook_raises_error(self):
        def bad_hook(db, ctx):
            raise RuntimeError("hook exploded")

        WorkflowEngine.register_hook("boom", bad_hook)

        states = (
            WorkflowState(name="A", sequence=1, on_exit_hooks=("boom",)),
            WorkflowState(name="B", sequence=2),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="fail_test", states=states, transitions=transitions)

        with pytest.raises(RuntimeError, match="hook exploded"):
            WorkflowEngine(wf).execute_transition(_make_db(), "A", "B", "Boss")

    def test_context_passed_to_hooks(self):
        received_ctx: list[dict] = []

        def capture_hook(db, ctx):
            received_ctx.append(ctx)

        WorkflowEngine.register_hook("capture", capture_hook)

        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="B", sequence=2, on_enter_hooks=("capture",)),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="ctx_test", states=states, transitions=transitions)

        ctx = {"item_id": 42, "reason": "test"}
        WorkflowEngine(wf).execute_transition(_make_db(), "A", "B", "Boss", context=ctx)

        assert len(received_ctx) == 1
        assert received_ctx[0]["item_id"] == 42

    def test_invalid_transition_raises_workflow_error(self):
        engine = WorkflowEngine(_linear_workflow())
        with pytest.raises(WorkflowError, match="No transition"):
            engine.execute_transition(_make_db(), "A", "C", "Boss")

    def test_role_denied_raises_workflow_error(self):
        engine = WorkflowEngine(_linear_workflow())
        with pytest.raises(WorkflowError, match="not allowed"):
            engine.execute_transition(_make_db(), "B", "C", "User")

    def test_unknown_current_state_raises(self):
        engine = WorkflowEngine(_linear_workflow())
        with pytest.raises(WorkflowError, match="Unknown current state"):
            engine.execute_transition(_make_db(), "Z", "A", "Boss")

    def test_unknown_target_state_raises(self):
        engine = WorkflowEngine(_linear_workflow())
        with pytest.raises(WorkflowError, match="Unknown target state"):
            engine.execute_transition(_make_db(), "A", "Z", "Boss")

    def test_no_hooks_returns_empty_tuple(self):
        engine = WorkflowEngine(_linear_workflow())
        result = engine.execute_transition(_make_db(), "A", "B", "Boss")
        assert result.hooks_executed == ()

    def test_default_context_is_empty_dict(self):
        """Passing no context should not raise."""
        engine = WorkflowEngine(_linear_workflow())
        result = engine.execute_transition(_make_db(), "A", "B", "Boss")
        assert result.success is True


# =============================================================================
# TestGetAllowedTransitions
# =============================================================================


class TestGetAllowedTransitions:
    """Tests for WorkflowEngine.get_allowed_transitions."""

    def test_returns_correct_options_for_role(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_allowed_transitions("A", "Boss") == ["B"]
        assert engine.get_allowed_transitions("B", "Boss") == ["C"]

    def test_role_restriction_filters_options(self):
        engine = WorkflowEngine(_linear_workflow())
        # User cannot go B -> C
        assert engine.get_allowed_transitions("B", "User") == []

    def test_empty_for_terminal_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_allowed_transitions("C", "Boss") == []

    def test_empty_for_unknown_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_allowed_transitions("Z", "Boss") == []

    def test_multiple_transitions_from_same_state(self):
        """When multiple transitions exist from one state, all allowed are returned."""
        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="B", sequence=2),
            WorkflowState(name="C", sequence=3),
        )
        transitions = (
            WorkflowTransition(from_state="A", to_state="B"),
            WorkflowTransition(from_state="A", to_state="C"),
        )
        wf = WorkflowDefinition(name="multi", states=states, transitions=transitions)
        engine = WorkflowEngine(wf)
        assert sorted(engine.get_allowed_transitions("A", "Anyone")) == ["B", "C"]


# =============================================================================
# TestGetNextState
# =============================================================================


class TestGetNextState:
    """Tests for WorkflowEngine.get_next_state."""

    def test_linear_sequence_works(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_next_state("A") == "B"
        assert engine.get_next_state("B") == "C"

    def test_returns_none_for_last_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_next_state("C") is None

    def test_returns_none_for_unknown_state(self):
        engine = WorkflowEngine(_linear_workflow())
        assert engine.get_next_state("Z") is None


# =============================================================================
# TestProductionWorkflowV1
# =============================================================================


class TestProductionWorkflowV1:
    """Tests for the legacy v1 production workflow."""

    def setup_method(self):
        self.wf = get_production_workflow_v1()
        self.engine = WorkflowEngine(self.wf)
        WorkflowEngine.clear_hooks()

    def test_workflow_name(self):
        assert self.wf.name == "production_v1"

    def test_full_walkthrough(self):
        db = _make_db()
        r1 = self.engine.execute_transition(db, "fabrication", "painting", "Boss")
        assert r1.success
        r2 = self.engine.execute_transition(db, "painting", "dispatch", "Boss")
        assert r2.success
        r3 = self.engine.execute_transition(db, "dispatch", "completed", "Boss")
        assert r3.success

    def test_skip_rejected(self):
        with pytest.raises(WorkflowError, match="No transition"):
            self.engine.execute_transition(_make_db(), "fabrication", "dispatch", "Boss")

    def test_completed_is_terminal(self):
        assert self.engine.get_allowed_transitions("completed", "Boss") == []

    def test_dispatch_to_completed_role_restricted(self):
        # User role should not be able to move to completed
        assert self.engine.validate_transition("dispatch", "completed", "User") is False
        assert self.engine.validate_transition("dispatch", "completed", "Boss") is True

    def test_sequence_order(self):
        assert self.engine.get_next_state("fabrication") == "painting"
        assert self.engine.get_next_state("painting") == "dispatch"
        assert self.engine.get_next_state("dispatch") == "completed"
        assert self.engine.get_next_state("completed") is None


# =============================================================================
# TestProductionWorkflowV3
# =============================================================================


class TestProductionWorkflowV3:
    """Tests for the v3 drawing-based production workflow."""

    def setup_method(self):
        self.wf = get_production_workflow_v3()
        self.engine = WorkflowEngine(self.wf)
        WorkflowEngine.clear_hooks()

    def test_workflow_name(self):
        assert self.wf.name == "production_v3"

    def test_has_seven_states(self):
        assert len(self.wf.states) == 7

    def test_full_walkthrough(self):
        db = _make_db()
        path = ["cutting", "drilling", "fitting", "welding", "painting", "qc", "dispatch"]
        for i in range(len(path) - 1):
            r = self.engine.execute_transition(db, path[i], path[i + 1], "Boss")
            assert r.success

    def test_skip_optional_drilling(self):
        """Drilling is optional, so cutting -> fitting should be allowed."""
        r = self.engine.execute_transition(_make_db(), "cutting", "fitting", "Boss")
        assert r.success

    def test_skip_optional_qc(self):
        """QC is optional, so painting -> dispatch is allowed for authorized roles."""
        r = self.engine.execute_transition(_make_db(), "painting", "dispatch", "Boss")
        assert r.success

    def test_cannot_skip_mandatory_stages(self):
        """Skipping a mandatory stage like welding should fail."""
        with pytest.raises(WorkflowError, match="No transition"):
            self.engine.execute_transition(_make_db(), "fitting", "painting", "Boss")

    def test_qc_to_dispatch_role_restricted(self):
        assert self.engine.validate_transition("qc", "dispatch", "User") is False
        assert self.engine.validate_transition("qc", "dispatch", "QA Inspector") is True

    def test_sequence_order(self):
        assert self.engine.get_next_state("cutting") == "drilling"
        assert self.engine.get_next_state("dispatch") is None


# =============================================================================
# TestDocumentWorkflow
# =============================================================================


class TestDocumentWorkflow:
    """Tests for the document status workflow."""

    def setup_method(self):
        self.wf = get_document_workflow()
        self.engine = WorkflowEngine(self.wf)
        WorkflowEngine.clear_hooks()

    def test_workflow_name(self):
        assert self.wf.name == "document_status"

    def test_draft_to_submitted_to_approved(self):
        db = _make_db()
        r1 = self.engine.execute_transition(db, "draft", "submitted", "User")
        assert r1.success
        r2 = self.engine.execute_transition(db, "submitted", "approved", "Boss")
        assert r2.success

    def test_cancel_from_draft(self):
        r = self.engine.execute_transition(_make_db(), "draft", "cancelled", "Boss")
        assert r.success

    def test_cancel_from_submitted(self):
        r = self.engine.execute_transition(_make_db(), "submitted", "cancelled", "Boss")
        assert r.success

    def test_cannot_cancel_from_approved(self):
        """Once approved, cancellation is not allowed."""
        with pytest.raises(WorkflowError, match="No transition"):
            self.engine.execute_transition(_make_db(), "approved", "cancelled", "Boss")

    def test_resubmit_rejected(self):
        """Cannot go from approved back to submitted."""
        with pytest.raises(WorkflowError, match="No transition"):
            self.engine.execute_transition(_make_db(), "approved", "submitted", "Boss")

    def test_user_cannot_approve(self):
        """Only Boss/Admin can approve."""
        with pytest.raises(WorkflowError, match="not allowed"):
            self.engine.execute_transition(_make_db(), "submitted", "approved", "User")

    def test_user_cannot_cancel(self):
        """Only Boss/Admin can cancel."""
        with pytest.raises(WorkflowError, match="not allowed"):
            self.engine.execute_transition(_make_db(), "draft", "cancelled", "User")


# =============================================================================
# TestHookRegistry
# =============================================================================


class TestHookRegistry:
    """Tests for the hook registration and execution."""

    def setup_method(self):
        WorkflowEngine.clear_hooks()

    def teardown_method(self):
        WorkflowEngine.clear_hooks()

    def test_register_and_execute_hook(self):
        called = []
        WorkflowEngine.register_hook("my_hook", lambda db, ctx: called.append(True))

        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="B", sequence=2, on_enter_hooks=("my_hook",)),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="hook_test", states=states, transitions=transitions)

        WorkflowEngine(wf).execute_transition(_make_db(), "A", "B", "Boss")
        assert called == [True]

    def test_missing_hook_raises_error(self):
        states = (
            WorkflowState(name="A", sequence=1, on_exit_hooks=("nonexistent",)),
            WorkflowState(name="B", sequence=2),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="missing_hook", states=states, transitions=transitions)

        with pytest.raises(WorkflowError, match="Hook 'nonexistent' is not registered"):
            WorkflowEngine(wf).execute_transition(_make_db(), "A", "B", "Boss")

    def test_clear_hooks(self):
        WorkflowEngine.register_hook("temp", lambda db, ctx: None)
        assert "temp" in WorkflowEngine._hooks
        WorkflowEngine.clear_hooks()
        assert "temp" not in WorkflowEngine._hooks

    def test_hook_receives_db_session(self):
        received_db = []

        def db_hook(db, ctx):
            received_db.append(db)

        WorkflowEngine.register_hook("db_check", db_hook)

        states = (
            WorkflowState(name="A", sequence=1),
            WorkflowState(name="B", sequence=2, on_enter_hooks=("db_check",)),
        )
        transitions = (WorkflowTransition(from_state="A", to_state="B"),)
        wf = WorkflowDefinition(name="db_test", states=states, transitions=transitions)

        mock_db = _make_db()
        WorkflowEngine(wf).execute_transition(mock_db, "A", "B", "Boss")
        assert received_db[0] is mock_db

    def test_overwrite_hook(self):
        """Registering the same hook name again overwrites it."""
        WorkflowEngine.register_hook("dup", lambda db, ctx: None)
        new_fn = lambda db, ctx: None  # noqa: E731
        WorkflowEngine.register_hook("dup", new_fn)
        assert WorkflowEngine._hooks["dup"] is new_fn


# =============================================================================
# TestLoadFromDB
# =============================================================================


class TestLoadFromDB:
    """Tests for load_workflow_from_db using a real test database."""

    def test_load_from_stage_config(self, db):
        """When StageConfig rows exist, they are loaded into a workflow."""
        from backend_core.app.models_v3 import StageConfig

        configs = [
            StageConfig(stage_name="cut", sequence=1, is_mandatory=True),
            StageConfig(stage_name="weld", sequence=2, is_mandatory=True),
            StageConfig(stage_name="ship", sequence=3, is_mandatory=True),
        ]
        for c in configs:
            db.add(c)
        db.commit()

        wf = load_workflow_from_db(db, "custom_pipeline")
        assert wf is not None
        assert wf.name == "custom_pipeline"
        assert len(wf.states) == 3
        assert [s.name for s in wf.states] == ["cut", "weld", "ship"]
        assert len(wf.transitions) == 2

    def test_fallback_when_not_configured(self, db):
        """When no StageConfig rows exist, None is returned."""
        wf = load_workflow_from_db(db, "nonexistent")
        assert wf is None

    def test_loaded_workflow_is_functional(self, db):
        """A workflow loaded from DB should work with the engine."""
        from backend_core.app.models_v3 import StageConfig

        configs = [
            StageConfig(stage_name="prep", sequence=1, is_mandatory=True),
            StageConfig(stage_name="build", sequence=2, is_mandatory=True),
            StageConfig(stage_name="done", sequence=3, is_mandatory=True),
        ]
        for c in configs:
            db.add(c)
        db.commit()

        wf = load_workflow_from_db(db, "db_workflow")
        engine = WorkflowEngine(wf)

        result = engine.execute_transition(db, "prep", "build", "Boss")
        assert result.success
        result = engine.execute_transition(db, "build", "done", "Boss")
        assert result.success


# =============================================================================
# TestWorkflowTransitionResult
# =============================================================================


class TestWorkflowTransitionResult:
    """Tests for the result dataclass."""

    def test_result_fields(self):
        r = WorkflowTransitionResult(
            success=True,
            from_state="A",
            to_state="B",
            hooks_executed=("h1", "h2"),
        )
        assert r.success is True
        assert r.from_state == "A"
        assert r.to_state == "B"
        assert r.hooks_executed == ("h1", "h2")

    def test_result_is_immutable(self):
        r = WorkflowTransitionResult(success=True, from_state="A", to_state="B")
        with pytest.raises(AttributeError):
            r.success = False
