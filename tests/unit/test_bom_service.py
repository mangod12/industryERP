"""
Unit tests for BOMService — Bill of Materials CRUD and import logic.

Tests:
  - Assembly CRUD: create, create with parts, weight calculation
  - Part CRUD: add, delete, weight recalculation
  - Material requirements: calculate, aggregation by section
  - Listing: filters by customer_id, search, lot_number
  - CSV import: fresh import, duplicate handling
"""
import pytest
from decimal import Decimal

from app.services.bom_service import BOMService
from app.models_bom import Assembly, AssemblyPart, AssemblyStageTracking

from tests.factories import create_customer, create_assembly, create_assembly_part


# ---------------------------------------------------------------------------
# Assembly CRUD
# ---------------------------------------------------------------------------


class TestCreateAssembly:
    """Tests for BOMService.create_assembly."""

    def test_create_assembly(self, db_session, boss_user):
        """Create a bare assembly and verify all fields are set correctly."""
        db = db_session
        customer = create_customer(db)

        assembly = BOMService.create_assembly(
            db=db,
            customer_id=customer.id,
            assembly_code="HR110",
            assembly_name="Handrail Type A",
            lot_number="LOT-01",
            ordered_qty=5,
        )

        assert assembly.id is not None
        assert assembly.assembly_code == "HR110"
        assert assembly.assembly_name == "Handrail Type A"
        assert assembly.lot_number == "LOT-01"
        assert assembly.ordered_qty == 5
        assert assembly.customer_id == customer.id
        assert assembly.current_stage == "fabrication"
        assert assembly.estimated_weight_kg == Decimal("0")

        # Stage tracking rows must exist for all 3 stages
        stages = (
            db.query(AssemblyStageTracking)
            .filter(AssemblyStageTracking.assembly_id == assembly.id)
            .all()
        )
        stage_names = sorted(st.stage for st in stages)
        assert stage_names == ["dispatch", "fabrication", "painting"]
        for st in stages:
            assert st.status == "pending"
            assert st.total_pieces == 0
            assert st.completed_pieces == 0

    def test_create_assembly_with_parts(self, db_session, boss_user):
        """Create assembly with inline parts; verify weight calculation and piece counts."""
        db = db_session
        customer = create_customer(db)

        parts_data = [
            {
                "mark_number": "HR110-01",
                "part_name": "Top Rail",
                "section": "40 NB(M) PIPE",
                "total_qty": 2,
                "weight_per_unit_kg": 3.09,
            },
            {
                "mark_number": "HR110-02",
                "part_name": "Bottom Rail",
                "section": "40 NB(M) PIPE",
                "total_qty": 3,
                "weight_per_unit_kg": 2.50,
            },
        ]

        assembly = BOMService.create_assembly(
            db=db,
            customer_id=customer.id,
            assembly_code="HR110",
            assembly_name="Handrail Type A",
            parts=parts_data,
        )

        # Weight: (2 * 3.09) + (3 * 2.50) = 6.18 + 7.50 = 13.68
        assert float(assembly.estimated_weight_kg) == pytest.approx(13.68, abs=0.01)

        # Parts created
        parts = db.query(AssemblyPart).filter(AssemblyPart.assembly_id == assembly.id).all()
        assert len(parts) == 2

        # Stage total_pieces = sum of total_qty = 2 + 3 = 5
        fab_stage = (
            db.query(AssemblyStageTracking)
            .filter(
                AssemblyStageTracking.assembly_id == assembly.id,
                AssemblyStageTracking.stage == "fabrication",
            )
            .first()
        )
        assert fab_stage.total_pieces == 5

    def test_create_assembly_invalid_customer(self, db_session, boss_user):
        """ValueError raised when customer_id does not exist."""
        with pytest.raises(ValueError, match="Customer ID"):
            BOMService.create_assembly(
                db=db_session,
                customer_id=99999,
                assembly_code="XX",
                assembly_name="Ghost",
            )


# ---------------------------------------------------------------------------
# Part CRUD
# ---------------------------------------------------------------------------


class TestPartCrud:
    """Tests for add_part and delete_part with weight recalculation."""

    def test_add_part(self, db_session, boss_user):
        """Add a part after creation; verify assembly weight and stage pieces recalculated."""
        db = db_session
        customer = create_customer(db)
        assembly = create_assembly(db, customer.id)

        part = BOMService.add_part(
            db,
            assembly.id,
            {
                "mark_number": "HR110-01",
                "part_name": "Top Rail",
                "section": "40 NB(M) PIPE",
                "total_qty": 4,
                "weight_per_unit_kg": 3.09,
            },
        )

        assert part.id is not None
        assert part.total_qty == 4
        assert float(part.total_weight_kg) == pytest.approx(12.36, abs=0.01)

        # Assembly weight should update
        db.refresh(assembly)
        assert float(assembly.estimated_weight_kg) == pytest.approx(12.36, abs=0.01)

        # Stage total_pieces should be 4
        fab = (
            db.query(AssemblyStageTracking)
            .filter(
                AssemblyStageTracking.assembly_id == assembly.id,
                AssemblyStageTracking.stage == "fabrication",
            )
            .first()
        )
        assert fab.total_pieces == 4

    def test_delete_part(self, db_session, boss_user):
        """Delete a part; verify assembly weight recalculated to zero."""
        db = db_session
        customer = create_customer(db)
        assembly = create_assembly(db, customer.id)
        part = create_assembly_part(db, assembly.id, total_qty=2, weight_per_unit_kg=5.0)

        # Before deletion, manually set assembly weight via recalculate
        BOMService._recalculate_assembly(db, assembly.id)
        db.commit()
        db.refresh(assembly)
        assert float(assembly.estimated_weight_kg) == pytest.approx(10.0, abs=0.01)

        BOMService.delete_part(db, part.id)

        db.refresh(assembly)
        assert float(assembly.estimated_weight_kg) == pytest.approx(0.0, abs=0.01)

        # No parts left
        remaining = db.query(AssemblyPart).filter(AssemblyPart.assembly_id == assembly.id).all()
        assert len(remaining) == 0

    def test_delete_nonexistent_part(self, db_session, boss_user):
        """ValueError raised for non-existent part ID."""
        with pytest.raises(ValueError, match="Part ID"):
            BOMService.delete_part(db_session, 99999)


# ---------------------------------------------------------------------------
# Material Requirements
# ---------------------------------------------------------------------------


class TestMaterialRequirements:
    """Tests for calculate_material_requirements."""

    def test_calculate_material_requirements(self, db_session, boss_user):
        """Create parts with same section, verify aggregation into single requirement."""
        db = db_session
        customer = create_customer(db)
        assembly = create_assembly(db, customer.id)

        # Two parts with the same section
        create_assembly_part(
            db, assembly.id,
            mark_number="P01", part_name="Part A",
            section="40 NB(M) PIPE", total_qty=2, weight_per_unit_kg=3.0,
        )
        create_assembly_part(
            db, assembly.id,
            mark_number="P02", part_name="Part B",
            section="40 NB(M) PIPE", total_qty=1, weight_per_unit_kg=5.0,
        )

        reqs = BOMService.calculate_material_requirements(db, assembly.id)

        assert len(reqs) == 1
        # Aggregated: (2*3.0) + (1*5.0) = 11.0
        assert float(reqs[0].required_qty_kg) == pytest.approx(11.0, abs=0.01)
        assert reqs[0].material_name == "40 NB(M) PIPE"

    def test_calculate_multi_section(self, db_session, boss_user):
        """Parts with different sections produce separate requirements."""
        db = db_session
        customer = create_customer(db)
        assembly = create_assembly(db, customer.id)

        create_assembly_part(
            db, assembly.id,
            mark_number="P01", section="PIPE", total_qty=1, weight_per_unit_kg=3.0,
        )
        create_assembly_part(
            db, assembly.id,
            mark_number="P02", section="ANGLE", total_qty=1, weight_per_unit_kg=2.0,
        )

        reqs = BOMService.calculate_material_requirements(db, assembly.id)

        assert len(reqs) == 2
        names = sorted(r.material_name for r in reqs)
        assert names == ["ANGLE", "PIPE"]

    def test_calculate_for_nonexistent_assembly(self, db_session, boss_user):
        """ValueError raised for non-existent assembly ID."""
        with pytest.raises(ValueError, match="Assembly ID"):
            BOMService.calculate_material_requirements(db_session, 99999)


# ---------------------------------------------------------------------------
# Listing & Filters
# ---------------------------------------------------------------------------


class TestListAssemblies:
    """Tests for list_assemblies with filters."""

    def test_list_assemblies_with_filters(self, db_session, boss_user):
        """Filter by customer_id, search, lot_number."""
        db = db_session
        cust_a = create_customer(db, name="Alpha Corp")
        cust_b = create_customer(db, name="Beta Corp")

        a1 = create_assembly(db, cust_a.id, assembly_code="HR110", lot_number="LOT-A")
        a2 = create_assembly(db, cust_a.id, assembly_code="HR120", lot_number="LOT-B")
        a3 = create_assembly(db, cust_b.id, assembly_code="BR200", lot_number="LOT-A")

        # Filter by customer
        results = BOMService.list_assemblies(db, customer_id=cust_a.id)
        assert len(results) == 2

        # Filter by lot_number
        results = BOMService.list_assemblies(db, lot_number="LOT-A")
        assert len(results) == 2
        codes = sorted(r.assembly_code for r in results)
        assert codes == ["BR200", "HR110"]

        # Search by code
        results = BOMService.list_assemblies(db, search="HR1")
        assert len(results) == 2

        # Combine customer + lot
        results = BOMService.list_assemblies(db, customer_id=cust_a.id, lot_number="LOT-B")
        assert len(results) == 1
        assert results[0].assembly_code == "HR120"


# ---------------------------------------------------------------------------
# CSV/Excel Import
# ---------------------------------------------------------------------------


class TestImportFromRows:
    """Tests for import_from_rows."""

    def test_import_from_rows(self, db_session, boss_user):
        """Import CSV-like rows; verify assemblies and parts created."""
        db = db_session
        customer = create_customer(db)

        rows = [
            {
                "assembly_code": "HR110",
                "assembly_name": "Handrail A",
                "lot_number": "LOT-01",
                "mark_number": "HR110-01",
                "part_name": "Top Rail",
                "section": "40 NB(M) PIPE",
                "total_qty": 2,
                "weight_per_unit_kg": 3.09,
            },
            {
                "assembly_code": "HR110",
                "assembly_name": "Handrail A",
                "lot_number": "LOT-01",
                "mark_number": "HR110-02",
                "part_name": "Bottom Rail",
                "section": "40 NB(M) PIPE",
                "total_qty": 1,
                "weight_per_unit_kg": 2.50,
            },
            {
                "assembly_code": "BR200",
                "assembly_name": "Bracket B",
                "lot_number": "LOT-02",
                "mark_number": "BR200-01",
                "part_name": "Base Plate",
                "section": "PLATE",
                "total_qty": 4,
                "weight_per_unit_kg": 1.20,
            },
        ]

        result = BOMService.import_from_rows(db, customer.id, rows)

        assert result["assemblies_created"] == 2
        assert result["parts_created"] == 3
        assert len(result["errors"]) == 0

        # Verify assemblies in DB
        assemblies = db.query(Assembly).filter(Assembly.customer_id == customer.id).all()
        assert len(assemblies) == 2

    def test_import_duplicate_assembly(self, db_session, boss_user):
        """Import rows for an existing assembly code; parts added to existing assembly."""
        db = db_session
        customer = create_customer(db)
        existing = create_assembly(
            db, customer.id,
            assembly_code="HR110",
            lot_number="LOT-01",
        )

        rows = [
            {
                "assembly_code": "HR110",
                "assembly_name": "Handrail A",
                "lot_number": "LOT-01",
                "mark_number": "HR110-01",
                "part_name": "Top Rail",
                "section": "PIPE",
                "total_qty": 1,
                "weight_per_unit_kg": 3.09,
            },
        ]

        result = BOMService.import_from_rows(db, customer.id, rows)

        # No new assemblies created (existing reused)
        assert result["assemblies_created"] == 0
        assert result["parts_created"] == 1
        assert any("already exists" in w for w in result["warnings"])

        # Part linked to the existing assembly
        parts = db.query(AssemblyPart).filter(AssemblyPart.assembly_id == existing.id).all()
        assert len(parts) == 1

    def test_import_missing_assembly_code(self, db_session, boss_user):
        """Rows without assembly_code produce errors."""
        db = db_session
        customer = create_customer(db)

        rows = [
            {
                "assembly_code": "",
                "mark_number": "P01",
                "part_name": "Orphan",
                "total_qty": 1,
                "weight_per_unit_kg": 1.0,
            },
        ]

        result = BOMService.import_from_rows(db, customer.id, rows)

        assert result["assemblies_created"] == 0
        assert result["parts_created"] == 0
        assert len(result["errors"]) == 1
        assert "missing assembly_code" in result["errors"][0].lower()
