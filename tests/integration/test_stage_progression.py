"""
Integration tests for stage progression via HTTP endpoints.

Tests the v1 tracking endpoints:
  POST /tracking/start-stage    — start a stage for a production item
  POST /tracking/complete-stage — complete a stage (triggers deduction on fabrication)

Also tests the v2 BOM stage piece tracking:
  PUT /api/v2/bom/assemblies/{id}/stages/{stage}/pieces
"""
import json
import pytest

from tests.factories import (
    create_customer,
    create_inventory_item,
    create_production_item,
    create_assembly,
    create_assembly_part,
)


# ---------------------------------------------------------------------------
# V1 tracking: start-stage / complete-stage
# ---------------------------------------------------------------------------


class TestV1StageProgression:
    """Tests for the legacy v1 tracking endpoints."""

    def test_start_and_complete_fabrication(self, client, boss_headers, db_session):
        """
        Create item -> Start fabrication -> Complete fabrication ->
        Verify stage completed and item advanced to painting.
        """
        customer = create_customer(db_session)
        inv = create_inventory_item(db_session, name="40 NB(M) PIPE", total=1000.0)
        item = create_production_item(
            db_session,
            customer_id=customer.id,
            item_code="SP-001",
            item_name="Stage Test Rail",
            section="40 NB(M) PIPE",
            weight_per_unit=3.09,
            material_requirements=json.dumps(
                [{"material_id": inv.id, "qty": 3.09}]
            ),
        )

        # Start fabrication
        start_resp = client.post(
            "/tracking/start-stage",
            json={"production_item_id": item.id, "stage": "fabrication"},
            headers=boss_headers,
        )
        assert start_resp.status_code == 200, start_resp.text
        assert start_resp.json()["status"] == "in_progress"
        assert start_resp.json()["stage"] == "fabrication"

        # Complete fabrication (triggers auto-deduction)
        complete_resp = client.post(
            "/tracking/complete-stage",
            json={"production_item_id": item.id, "stage": "fabrication"},
            headers=boss_headers,
        )
        assert complete_resp.status_code == 200, complete_resp.text
        assert complete_resp.json()["status"] == "completed"

        # Verify inventory was deducted
        db_session.refresh(inv)
        assert inv.used == pytest.approx(3.09, abs=0.01)

        # Verify item advanced to painting
        db_session.refresh(item)
        assert item.current_stage == "painting"
        assert item.fabrication_deducted is True

    def test_cannot_start_painting_before_fabrication_complete(
        self, client, boss_headers, db_session
    ):
        """Starting painting before fabrication is completed returns 400."""
        customer = create_customer(db_session)
        item = create_production_item(db_session, customer_id=customer.id)

        resp = client.post(
            "/tracking/start-stage",
            json={"production_item_id": item.id, "stage": "painting"},
            headers=boss_headers,
        )
        assert resp.status_code == 400
        assert "previous stage" in resp.json()["detail"].lower()

    def test_complete_not_in_progress_returns_400(
        self, client, boss_headers, db_session
    ):
        """Completing a stage that is not in_progress returns 400."""
        customer = create_customer(db_session)
        item = create_production_item(db_session, customer_id=customer.id)

        resp = client.post(
            "/tracking/complete-stage",
            json={"production_item_id": item.id, "stage": "fabrication"},
            headers=boss_headers,
        )
        assert resp.status_code == 400
        assert "not in progress" in resp.json()["detail"].lower()

    def test_full_three_stage_progression(self, client, boss_headers, db_session):
        """Walk through all three stages: fabrication -> painting -> dispatch -> completed."""
        customer = create_customer(db_session)
        item = create_production_item(db_session, customer_id=customer.id)

        for stage in ["fabrication", "painting", "dispatch"]:
            start = client.post(
                "/tracking/start-stage",
                json={"production_item_id": item.id, "stage": stage},
                headers=boss_headers,
            )
            assert start.status_code == 200, f"Failed to start {stage}: {start.text}"

            complete = client.post(
                "/tracking/complete-stage",
                json={"production_item_id": item.id, "stage": stage},
                headers=boss_headers,
            )
            assert complete.status_code == 200, f"Failed to complete {stage}: {complete.text}"

        db_session.refresh(item)
        assert item.current_stage == "completed"


# ---------------------------------------------------------------------------
# V2 BOM stage piece tracking
# ---------------------------------------------------------------------------


class TestV2BomStageProgression:
    """Tests for the BOM per-piece stage tracking via HTTP."""

    def test_incremental_piece_completion(self, client, boss_headers, db_session):
        """Incrementally complete pieces and verify progress."""
        customer = create_customer(db_session, name="V2 Stage Corp")
        assembly = create_assembly(db_session, customer.id, assembly_code="V2S-001")
        create_assembly_part(
            db_session, assembly.id,
            mark_number="V2S-01",
            part_name="Beam",
            total_qty=10,
            weight_per_unit_kg=2.0,
        )
        # Sync stage total_pieces
        for st in assembly.stage_tracking:
            st.total_pieces = 10
            db_session.add(st)
        db_session.commit()

        # Complete 3 pieces
        resp1 = client.put(
            f"/api/v2/bom/assemblies/{assembly.id}/stages/fabrication/pieces",
            json={"completed_delta": 3},
            headers=boss_headers,
        )
        assert resp1.status_code == 200
        assert resp1.json()["completed_pieces"] == 3
        assert resp1.json()["status"] == "in_progress"

        # Complete 7 more (total = 10, auto-complete)
        resp2 = client.put(
            f"/api/v2/bom/assemblies/{assembly.id}/stages/fabrication/pieces",
            json={"completed_delta": 7},
            headers=boss_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["completed_pieces"] == 10
        assert resp2.json()["auto_completed"] is True
        assert resp2.json()["status"] == "completed"

        # Assembly should advance to painting
        db_session.refresh(assembly)
        assert assembly.current_stage == "painting"

    def test_exceed_pieces_returns_400(self, client, boss_headers, db_session):
        """Exceeding total pieces returns 400."""
        customer = create_customer(db_session, name="Exceed Corp")
        assembly = create_assembly(db_session, customer.id, assembly_code="EXC-001")
        create_assembly_part(
            db_session, assembly.id,
            mark_number="EXC-01",
            total_qty=5,
            weight_per_unit_kg=1.0,
        )
        for st in assembly.stage_tracking:
            st.total_pieces = 5
            db_session.add(st)
        db_session.commit()

        resp = client.put(
            f"/api/v2/bom/assemblies/{assembly.id}/stages/fabrication/pieces",
            json={"completed_delta": 6},
            headers=boss_headers,
        )
        assert resp.status_code == 400
        assert "exceed" in resp.json()["detail"].lower()
