"""
Unit tests for StageService — Per-piece completion tracking for assemblies.

Tests:
  - Happy path: increment completed pieces
  - Auto-complete: all pieces done triggers stage completion
  - Exceed total: ValueError when delta would exceed total
  - Negative delta: clamped to 0 (no negative completed count)
  - Completed stage rejects update: ValueError on already-completed stage
  - Assembly progress: correct summary format
  - Progress dashboard: aggregation across assemblies
"""
import pytest

from app.services.stage_service import StageService
from app.models_bom import AssemblyStageTracking

from tests.factories import (
    create_customer,
    create_assembly,
    create_assembly_part,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_assembly_with_parts(db, total_qty=5):
    """Create a customer, assembly, and part; return (assembly, boss-user-id placeholder)."""
    customer = create_customer(db)
    assembly = create_assembly(db, customer.id)
    create_assembly_part(
        db, assembly.id,
        mark_number="P01",
        part_name="Rail",
        total_qty=total_qty,
        weight_per_unit_kg=2.0,
    )
    # Manually sync stage total_pieces (factory doesn't auto-calc)
    for st in assembly.stage_tracking:
        st.total_pieces = total_qty
        db.add(st)
    db.commit()
    db.refresh(assembly)
    return assembly


# ---------------------------------------------------------------------------
# update_piece_count
# ---------------------------------------------------------------------------


class TestUpdatePieceCount:
    """Tests for StageService.update_piece_count."""

    def test_update_piece_count_happy_path(self, db_session, boss_user):
        """Increment pieces; verify counts and in_progress status."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=10)

        result = StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=3, user_id=boss_user.id,
        )

        assert result["completed_pieces"] == 3
        assert result["total_pieces"] == 10
        assert result["status"] == "in_progress"
        assert result["auto_completed"] is False
        assert result["percentage"] == pytest.approx(30.0, abs=0.1)

    def test_auto_complete_stage(self, db_session, boss_user):
        """Increment to total_pieces; verify auto-complete and stage advance."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=5)

        result = StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=5, user_id=boss_user.id,
        )

        assert result["auto_completed"] is True
        assert result["status"] == "completed"
        assert result["completed_pieces"] == 5
        assert result["percentage"] == pytest.approx(100.0, abs=0.1)

        # Assembly current_stage should advance to "painting"
        db.refresh(assembly)
        assert assembly.current_stage == "painting"

    def test_exceed_total_pieces(self, db_session, boss_user):
        """ValueError when delta would exceed total_pieces."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=5)

        with pytest.raises(ValueError, match="Cannot exceed total pieces"):
            StageService.update_piece_count(
                db, assembly.id, "fabrication", completed_delta=6, user_id=boss_user.id,
            )

    def test_negative_delta_clamped(self, db_session, boss_user):
        """Negative delta clamps completed_pieces to 0 (never goes below zero)."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=5)

        # First increment to 2
        StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=2, user_id=boss_user.id,
        )

        # Decrease by more than current (should clamp to 0)
        result = StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=-5, user_id=boss_user.id,
        )

        assert result["completed_pieces"] == 0

    def test_completed_stage_rejects_update(self, db_session, boss_user):
        """ValueError when trying to update an already-completed stage."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=3)

        # Complete the stage
        StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=3, user_id=boss_user.id,
        )

        # Try to update again
        with pytest.raises(ValueError, match="already completed"):
            StageService.update_piece_count(
                db, assembly.id, "fabrication", completed_delta=1, user_id=boss_user.id,
            )

    def test_invalid_stage_name(self, db_session, boss_user):
        """ValueError for a stage name not in STAGES."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=3)

        with pytest.raises(ValueError, match="Invalid stage"):
            StageService.update_piece_count(
                db, assembly.id, "welding", completed_delta=1, user_id=boss_user.id,
            )

    def test_nonexistent_assembly(self, db_session, boss_user):
        """ValueError when assembly does not exist."""
        with pytest.raises(ValueError, match="not found"):
            StageService.update_piece_count(
                db_session, 99999, "fabrication", completed_delta=1, user_id=boss_user.id,
            )


# ---------------------------------------------------------------------------
# get_assembly_progress
# ---------------------------------------------------------------------------


class TestGetAssemblyProgress:
    """Tests for StageService.get_assembly_progress."""

    def test_get_assembly_progress(self, db_session, boss_user):
        """Verify progress summary includes stages and parts with correct format."""
        db = db_session
        assembly = _setup_assembly_with_parts(db, total_qty=10)

        # Update some pieces
        StageService.update_piece_count(
            db, assembly.id, "fabrication", completed_delta=4, user_id=boss_user.id,
        )

        progress = StageService.get_assembly_progress(db, assembly.id)

        assert progress["assembly_id"] == assembly.id
        assert progress["assembly_code"] == assembly.assembly_code
        assert progress["current_stage"] == "fabrication"

        # Stages list should have 3 entries
        assert len(progress["stages"]) == 3
        fab = next(s for s in progress["stages"] if s["stage"] == "fabrication")
        assert fab["total_pieces"] == 10
        assert fab["completed_pieces"] == 4
        assert fab["percentage"] == pytest.approx(40.0, abs=0.1)

        # Parts list should have 1 entry
        assert len(progress["parts"]) == 1
        assert progress["parts"][0]["mark_number"] == "P01"

    def test_progress_nonexistent_assembly(self, db_session, boss_user):
        """ValueError for non-existent assembly."""
        with pytest.raises(ValueError, match="not found"):
            StageService.get_assembly_progress(db_session, 99999)


# ---------------------------------------------------------------------------
# get_progress_dashboard
# ---------------------------------------------------------------------------


class TestGetProgressDashboard:
    """Tests for StageService.get_progress_dashboard."""

    def test_get_progress_dashboard(self, db_session, boss_user):
        """Verify aggregation across multiple assemblies."""
        db = db_session
        customer = create_customer(db)

        asm1 = create_assembly(db, customer.id, assembly_code="A1", lot_number="L1")
        create_assembly_part(db, asm1.id, mark_number="A1-P01", total_qty=5, weight_per_unit_kg=1.0)
        for st in asm1.stage_tracking:
            st.total_pieces = 5
            db.add(st)

        asm2 = create_assembly(db, customer.id, assembly_code="A2", lot_number="L2")
        create_assembly_part(db, asm2.id, mark_number="A2-P01", total_qty=3, weight_per_unit_kg=1.0)
        for st in asm2.stage_tracking:
            st.total_pieces = 3
            db.add(st)

        db.commit()

        # Complete some pieces
        StageService.update_piece_count(db, asm1.id, "fabrication", 2, boss_user.id)
        StageService.update_piece_count(db, asm2.id, "fabrication", 1, boss_user.id)

        dashboard = StageService.get_progress_dashboard(db)

        assert dashboard["total_assemblies"] == 2

        fab = next((s for s in dashboard["stages"] if s["stage"] == "fabrication"), None)
        assert fab is not None
        assert fab["total_pieces"] == 8  # 5 + 3
        assert fab["completed_pieces"] == 3  # 2 + 1

    def test_dashboard_filter_by_customer(self, db_session, boss_user):
        """Dashboard filters by customer_id."""
        db = db_session
        cust_a = create_customer(db, name="Alpha")
        cust_b = create_customer(db, name="Beta")

        asm_a = create_assembly(db, cust_a.id, assembly_code="AA", lot_number="L-A")
        create_assembly_part(db, asm_a.id, mark_number="AA-01", total_qty=4, weight_per_unit_kg=1.0)
        for st in asm_a.stage_tracking:
            st.total_pieces = 4
            db.add(st)

        asm_b = create_assembly(db, cust_b.id, assembly_code="BB", lot_number="L-B")
        create_assembly_part(db, asm_b.id, mark_number="BB-01", total_qty=6, weight_per_unit_kg=1.0)
        for st in asm_b.stage_tracking:
            st.total_pieces = 6
            db.add(st)

        db.commit()

        dashboard = StageService.get_progress_dashboard(db, customer_id=cust_a.id)

        assert dashboard["total_assemblies"] == 1
        fab = next((s for s in dashboard["stages"] if s["stage"] == "fabrication"), None)
        assert fab is not None
        assert fab["total_pieces"] == 4
