"""
Configurable workflow engine inspired by ERPNext's Workflow doctype.
Handles both production stage flows and document status workflows.

The engine is stateless: it takes the current state as input and returns
the new state after validation and hook execution. Workflow definitions
are pure data (dataclasses) that describe states, transitions, and hooks.

Usage:
    engine = WorkflowEngine(get_production_workflow_v1())
    result = engine.execute_transition(db, "fabrication", "painting", "Boss", context={})
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

# =============================================================================
# EXCEPTIONS
# =============================================================================


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass(frozen=True)
class WorkflowState:
    """A single state in a workflow."""

    name: str
    sequence: int
    is_mandatory: bool = True
    allowed_roles: tuple[str, ...] = ()
    on_enter_hooks: tuple[str, ...] = ()
    on_exit_hooks: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowTransition:
    """A permitted transition between two states."""

    from_state: str
    to_state: str
    allowed_roles: tuple[str, ...] = ()
    condition: str | None = None


@dataclass(frozen=True)
class WorkflowTransitionResult:
    """Outcome of an executed transition."""

    success: bool
    from_state: str
    to_state: str
    hooks_executed: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowDefinition:
    """Defines a workflow with states, transitions, and hooks.

    Invariants enforced at construction:
    - No duplicate state names
    - All transitions reference valid states
    """

    name: str
    states: tuple[WorkflowState, ...]
    transitions: tuple[WorkflowTransition, ...]

    def __post_init__(self) -> None:
        state_names = [s.name for s in self.states]
        if len(state_names) != len(set(state_names)):
            duplicates = [n for n in state_names if state_names.count(n) > 1]
            raise WorkflowError(f"Duplicate state names in workflow '{self.name}': {set(duplicates)}")
        if not self.states:
            raise WorkflowError(f"Workflow '{self.name}' must have at least one state")
        valid = set(state_names)
        for t in self.transitions:
            if t.from_state not in valid:
                raise WorkflowError(f"Transition references unknown from_state '{t.from_state}'")
            if t.to_state not in valid:
                raise WorkflowError(f"Transition references unknown to_state '{t.to_state}'")

    def get_state(self, name: str) -> WorkflowState | None:
        """Return the state with the given name, or None."""
        for s in self.states:
            if s.name == name:
                return s
        return None


# =============================================================================
# ENGINE
# =============================================================================


class WorkflowEngine:
    """Executes workflow transitions with validation and hooks.

    The engine is stateless — it does not store the current state of any
    entity. Instead, the caller passes in the current state and gets back
    a result with the new state.

    Hooks are registered globally via ``register_hook`` and referenced by
    name in WorkflowState definitions.
    """

    _hooks: dict[str, Callable[[Session, dict], None]] = {}

    @classmethod
    def register_hook(cls, name: str, func: Callable[[Session, dict], None]) -> None:
        """Register a named hook function.

        Hook signature: ``(db: Session, context: dict) -> None``
        """
        cls._hooks[name] = func

    @classmethod
    def clear_hooks(cls) -> None:
        """Remove all registered hooks (useful in tests)."""
        cls._hooks.clear()

    def __init__(self, workflow: WorkflowDefinition) -> None:
        self.workflow = workflow

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def validate_transition(self, current_state: str, target_state: str, user_role: str) -> bool:
        """Check if a transition is allowed.

        Returns True when a matching transition exists and the user's role
        is permitted (or the transition has no role restriction).
        """
        for t in self.workflow.transitions:
            if t.from_state == current_state and t.to_state == target_state:
                if t.allowed_roles and user_role not in t.allowed_roles:
                    return False
                return True
        return False

    def get_allowed_transitions(self, current_state: str, user_role: str) -> list[str]:
        """Return the list of states reachable from *current_state* for *user_role*."""
        result: list[str] = []
        for t in self.workflow.transitions:
            if t.from_state == current_state:
                if not t.allowed_roles or user_role in t.allowed_roles:
                    result.append(t.to_state)
        return result

    def get_next_state(self, current_state: str) -> str | None:
        """Return the next state in sequence order, or None for the last state."""
        current = self.workflow.get_state(current_state)
        if current is None:
            return None
        sorted_states = sorted(self.workflow.states, key=lambda s: s.sequence)
        for s in sorted_states:
            if s.sequence > current.sequence:
                return s.name
        return None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_transition(
        self,
        db: Session,
        current_state: str,
        target_state: str,
        user_role: str,
        context: dict | None = None,
    ) -> WorkflowTransitionResult:
        """Execute a state transition with hooks.

        Steps:
        1. Validate the transition is allowed
        2. Fire on_exit hooks for the current state
        3. Fire on_enter hooks for the target state
        4. Return result with new state

        Raises ``WorkflowError`` if the transition is invalid or a hook fails.
        """
        if context is None:
            context = {}

        # Validate current state exists
        current = self.workflow.get_state(current_state)
        if current is None:
            raise WorkflowError(f"Unknown current state '{current_state}'")

        target = self.workflow.get_state(target_state)
        if target is None:
            raise WorkflowError(f"Unknown target state '{target_state}'")

        if not self.validate_transition(current_state, target_state, user_role):
            # Determine a specific reason
            transition_exists = any(
                t.from_state == current_state and t.to_state == target_state for t in self.workflow.transitions
            )
            if transition_exists:
                raise WorkflowError(
                    f"Role '{user_role}' is not allowed to transition from '{current_state}' to '{target_state}'"
                )
            raise WorkflowError(
                f"No transition from '{current_state}' to '{target_state}' in workflow '{self.workflow.name}'"
            )

        hooks_executed: list[str] = []

        # Fire on_exit hooks for current state
        for hook_name in current.on_exit_hooks:
            self._run_hook(hook_name, db, context)
            hooks_executed.append(hook_name)

        # Fire on_enter hooks for target state
        for hook_name in target.on_enter_hooks:
            self._run_hook(hook_name, db, context)
            hooks_executed.append(hook_name)

        return WorkflowTransitionResult(
            success=True,
            from_state=current_state,
            to_state=target_state,
            hooks_executed=tuple(hooks_executed),
        )

    def _run_hook(self, hook_name: str, db: Session, context: dict) -> None:
        """Look up and execute a named hook."""
        func = self._hooks.get(hook_name)
        if func is None:
            raise WorkflowError(f"Hook '{hook_name}' is not registered")
        func(db, context)


# =============================================================================
# BUILT-IN WORKFLOW DEFINITIONS
# =============================================================================

_ALL_ROLES = ("Boss", "Admin", "Store Keeper", "QA Inspector", "Dispatch Operator", "User")


def get_production_workflow_v1() -> WorkflowDefinition:
    """Legacy v1 stage flow: fabrication -> painting -> dispatch -> completed.

    Maps directly to the STAGE_FLOW dict in tracking_service.py.
    """
    states = (
        WorkflowState(name="fabrication", sequence=1, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="painting", sequence=2, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(
            name="dispatch", sequence=3, is_mandatory=True, allowed_roles=("Boss", "Admin", "Dispatch Operator")
        ),
        WorkflowState(name="completed", sequence=4, is_mandatory=True, allowed_roles=("Boss", "Admin")),
    )
    transitions = (
        WorkflowTransition(from_state="fabrication", to_state="painting", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="painting", to_state="dispatch", allowed_roles=_ALL_ROLES),
        WorkflowTransition(
            from_state="dispatch", to_state="completed", allowed_roles=("Boss", "Admin", "Dispatch Operator")
        ),
    )
    return WorkflowDefinition(name="production_v1", states=states, transitions=transitions)


def get_production_workflow_v3() -> WorkflowDefinition:
    """v3 stage flow: cutting -> drilling -> fitting -> welding -> painting -> qc -> dispatch.

    Maps to DEFAULT_STAGES in models_v3.py.
    """
    states = (
        WorkflowState(name="cutting", sequence=1, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="drilling", sequence=2, is_mandatory=False, allowed_roles=_ALL_ROLES),
        WorkflowState(name="fitting", sequence=3, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="welding", sequence=4, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="painting", sequence=5, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="qc", sequence=6, is_mandatory=False, allowed_roles=("Boss", "Admin", "QA Inspector")),
        WorkflowState(
            name="dispatch", sequence=7, is_mandatory=True, allowed_roles=("Boss", "Admin", "Dispatch Operator")
        ),
    )
    transitions = (
        WorkflowTransition(from_state="cutting", to_state="drilling", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="drilling", to_state="fitting", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="fitting", to_state="welding", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="welding", to_state="painting", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="painting", to_state="qc", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="qc", to_state="dispatch", allowed_roles=("Boss", "Admin", "QA Inspector")),
        # Allow skipping optional stages
        WorkflowTransition(from_state="cutting", to_state="fitting", allowed_roles=_ALL_ROLES),
        WorkflowTransition(
            from_state="painting", to_state="dispatch", allowed_roles=("Boss", "Admin", "Dispatch Operator")
        ),
    )
    return WorkflowDefinition(name="production_v3", states=states, transitions=transitions)


def get_document_workflow() -> WorkflowDefinition:
    """Document status flow: draft -> submitted -> approved | cancelled.

    For GRN, dispatch notes, and other documents. Cancellation is allowed
    from draft and submitted states.
    """
    states = (
        WorkflowState(name="draft", sequence=1, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="submitted", sequence=2, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="approved", sequence=3, is_mandatory=True, allowed_roles=("Boss", "Admin")),
        WorkflowState(name="cancelled", sequence=4, is_mandatory=False, allowed_roles=("Boss", "Admin")),
    )
    transitions = (
        WorkflowTransition(from_state="draft", to_state="submitted", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="submitted", to_state="approved", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="draft", to_state="cancelled", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="submitted", to_state="cancelled", allowed_roles=("Boss", "Admin")),
    )
    return WorkflowDefinition(name="document_status", states=states, transitions=transitions)


def get_grn_workflow() -> WorkflowDefinition:
    """GRN document workflow with hooks for lot creation and cancellation."""
    states = (
        WorkflowState(name="draft", sequence=1, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="submitted", sequence=2, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(
            name="approved",
            sequence=3,
            is_mandatory=True,
            allowed_roles=("Boss", "Admin"),
            on_enter_hooks=("on_grn_approve",),
        ),
        WorkflowState(
            name="cancelled",
            sequence=4,
            is_mandatory=False,
            allowed_roles=("Boss", "Admin"),
            on_enter_hooks=("on_grn_cancel",),
        ),
    )
    transitions = (
        WorkflowTransition(from_state="draft", to_state="submitted", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="submitted", to_state="approved", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="draft", to_state="cancelled", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="submitted", to_state="cancelled", allowed_roles=("Boss", "Admin")),
    )
    return WorkflowDefinition(name="grn_workflow", states=states, transitions=transitions)


def get_dispatch_workflow() -> WorkflowDefinition:
    """Dispatch document workflow with hooks for stock deduction and cancellation."""
    states = (
        WorkflowState(name="draft", sequence=1, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(name="submitted", sequence=2, is_mandatory=True, allowed_roles=_ALL_ROLES),
        WorkflowState(
            name="approved",
            sequence=3,
            is_mandatory=True,
            allowed_roles=("Boss", "Admin"),
            on_enter_hooks=("on_dispatch_approve",),
        ),
        WorkflowState(
            name="cancelled",
            sequence=4,
            is_mandatory=False,
            allowed_roles=("Boss", "Admin"),
            on_enter_hooks=("on_dispatch_cancel",),
        ),
    )
    transitions = (
        WorkflowTransition(from_state="draft", to_state="submitted", allowed_roles=_ALL_ROLES),
        WorkflowTransition(from_state="submitted", to_state="approved", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="draft", to_state="cancelled", allowed_roles=("Boss", "Admin")),
        WorkflowTransition(from_state="submitted", to_state="cancelled", allowed_roles=("Boss", "Admin")),
    )
    return WorkflowDefinition(name="dispatch_workflow", states=states, transitions=transitions)


# =============================================================================
# DOCUMENT WORKFLOW HOOKS & HELPERS
# =============================================================================

_document_hooks_registered = False


def on_grn_approve(db: Session, context: dict) -> None:
    """Hook: create stock lots when GRN is approved.

    Expects context keys: grn_id, user_id, location_id.
    Sets context["created_lots"] with the list of created StockLot objects.

    Note: status change is handled by ``transition_document``.  This hook
    only performs the business-logic side effects (lot creation, QA check).
    """
    from datetime import datetime

    from ..models_v2 import GoodsReceiptNote, QAStatus
    from .inventory_service import InvalidOperationError, StockLotService

    grn_id = context["grn_id"]
    user_id = context["user_id"]
    location_id = context["location_id"]

    grn = db.query(GoodsReceiptNote).filter(GoodsReceiptNote.id == grn_id).with_for_update().first()

    if not grn:
        raise WorkflowError(f"GRN {grn_id} not found")

    # Validate all line items have QA decision
    pending_qa = [li for li in grn.line_items if li.qa_status == QAStatus.PENDING]
    if pending_qa:
        raise InvalidOperationError(f"{len(pending_qa)} line items pending QA inspection")

    created_lots = []
    for line in grn.line_items:
        if line.qa_status in (QAStatus.APPROVED, QAStatus.CONDITIONAL):
            lot = StockLotService.create_lot_from_grn(db, line, location_id, user_id)
            created_lots.append(lot)

    grn.approved_by = user_id
    grn.received_time = datetime.utcnow()
    grn.updated_at = datetime.utcnow()

    context["grn"] = grn
    context["created_lots"] = created_lots


def on_grn_cancel(db: Session, context: dict) -> None:
    """Hook: mark GRN as cancelled.

    Expects context keys: grn_id, reason (optional).
    """
    from datetime import datetime

    from ..models_v2 import GoodsReceiptNote

    grn_id = context["grn_id"]
    reason = context.get("reason", "")
    grn = db.query(GoodsReceiptNote).filter(GoodsReceiptNote.id == grn_id).first()
    if grn:
        grn.remarks = f"{grn.remarks or ''}\n[CANCELLED] {reason}".strip()
        grn.updated_at = datetime.utcnow()
        context["grn"] = grn


def on_dispatch_approve(db: Session, context: dict) -> None:
    """Hook: deduct stock when dispatch is approved.

    Expects context keys: dispatch_id, user_id.
    Sets context["movements"] with the result.
    """
    from datetime import datetime

    from ..models_v2 import DispatchNote
    from .inventory_service import StockLotService

    dispatch_id = context["dispatch_id"]
    user_id = context["user_id"]
    dispatch = db.query(DispatchNote).filter(DispatchNote.id == dispatch_id).with_for_update().first()

    if not dispatch:
        raise WorkflowError(f"Dispatch note {dispatch_id} not found")

    movements = []
    for line in dispatch.line_items:
        movement, lot = StockLotService.consume_from_lot(
            db=db,
            lot_id=line.stock_lot_id,
            weight_kg=line.dispatched_weight_kg,
            user_id=user_id,
            reason=f"Dispatch {dispatch.dispatch_number}",
            reference_type="dispatch",
            reference_id=dispatch.id,
        )
        movements.append(
            {
                "lot_number": lot.lot_number,
                "movement_number": movement.movement_number,
                "weight_dispatched": float(line.dispatched_weight_kg),
                "remaining_weight": float(lot.current_weight_kg),
            }
        )

    dispatch.approved_by = user_id
    dispatch.dispatched_at = datetime.utcnow()
    dispatch.updated_at = datetime.utcnow()
    context["dispatch"] = dispatch
    context["movements"] = movements


def on_dispatch_cancel(db: Session, context: dict) -> None:
    """Hook: mark dispatch as cancelled.

    Expects context keys: dispatch_id, reason (optional).
    """
    from datetime import datetime

    from ..models_v2 import DispatchNote

    dispatch_id = context["dispatch_id"]
    reason = context.get("reason", "")
    dispatch = db.query(DispatchNote).filter(DispatchNote.id == dispatch_id).first()
    if dispatch:
        dispatch.remarks = f"{dispatch.remarks or ''}\n[CANCELLED] {reason}".strip()
        dispatch.updated_at = datetime.utcnow()
        context["dispatch"] = dispatch


def register_document_hooks() -> None:
    """Register all document workflow hooks with the engine.

    Safe to call multiple times — only registers once.
    """
    global _document_hooks_registered
    if _document_hooks_registered:
        return
    WorkflowEngine.register_hook("on_grn_approve", on_grn_approve)
    WorkflowEngine.register_hook("on_grn_cancel", on_grn_cancel)
    WorkflowEngine.register_hook("on_dispatch_approve", on_dispatch_approve)
    WorkflowEngine.register_hook("on_dispatch_cancel", on_dispatch_cancel)
    _document_hooks_registered = True


def transition_document(
    db: Session,
    document,
    target_status: str,
    user_role: str,
    context: dict | None = None,
) -> WorkflowTransitionResult:
    """Convenience function to transition a GRN/DispatchNote through its workflow.

    Automatically selects the correct workflow (GRN or dispatch) based on
    the document type.  Falls back to the generic document workflow for
    unknown types.

    Args:
        db: Database session.
        document: A GRN or DispatchNote instance (must have a ``.status`` attribute).
        target_status: The desired target state name (e.g. "submitted", "approved").
        user_role: The role of the user performing the transition.
        context: Extra data passed to hooks (e.g. grn_id, user_id, location_id).

    Returns:
        WorkflowTransitionResult with the outcome.

    Raises:
        WorkflowError if the transition is invalid or a hook fails.
    """
    from ..models_v2 import DispatchNote, DocumentStatus, GoodsReceiptNote

    register_document_hooks()

    # Select the right workflow based on document type
    if isinstance(document, GoodsReceiptNote):
        workflow = get_grn_workflow()
    elif isinstance(document, DispatchNote):
        workflow = get_dispatch_workflow()
    else:
        workflow = get_document_workflow()

    engine = WorkflowEngine(workflow)
    current_status = document.status.value
    result = engine.execute_transition(db, current_status, target_status, user_role, context or {})
    document.status = DocumentStatus(result.to_state)
    return result


def load_workflow_from_db(db: Session, workflow_name: str) -> WorkflowDefinition | None:
    """Load a workflow from the v3 StageConfig table if configured.

    Falls back to None if no rows exist for the given workflow name (caller
    should use a default workflow in that case).
    """
    from ..models_v3 import StageConfig

    rows = db.query(StageConfig).filter(StageConfig.customer_id.is_(None)).order_by(StageConfig.sequence).all()
    if not rows:
        return None

    states: list[WorkflowState] = []
    transitions: list[WorkflowTransition] = []

    for row in rows:
        states.append(
            WorkflowState(
                name=row.stage_name,
                sequence=row.sequence,
                is_mandatory=row.is_mandatory,
                allowed_roles=_ALL_ROLES,
            )
        )

    # Build linear transitions from sequential states
    for i in range(len(states) - 1):
        transitions.append(
            WorkflowTransition(
                from_state=states[i].name,
                to_state=states[i + 1].name,
                allowed_roles=_ALL_ROLES,
            )
        )

    return WorkflowDefinition(
        name=workflow_name,
        states=tuple(states),
        transitions=tuple(transitions),
    )
