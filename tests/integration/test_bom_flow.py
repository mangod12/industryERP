"""
Integration tests for the full BOM lifecycle via HTTP endpoints.

Tests exercise real HTTP calls through TestClient against:
  POST /api/v2/bom/assemblies               (create assembly)
  POST /api/v2/bom/assemblies/{id}/parts     (add part)
  GET  /api/v2/bom/assemblies/{id}           (get detail)
  POST /api/v2/bom/assemblies/{id}/calculate-materials
  PUT  /api/v2/bom/assemblies/{id}/stages/{stage}/pieces
  GET  /api/v2/bom/assemblies/{id}/progress
"""
import pytest

from tests.factories import create_customer


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


class TestFullBomLifecycle:
    """End-to-end: customer -> assembly -> parts -> materials -> pieces -> progress."""

    def test_full_bom_lifecycle(self, client, boss_headers, db_session):
        """
        Create customer -> Create assembly -> Add parts ->
        Calculate materials -> Update pieces -> Verify progress.
        """
        # 1. Create a customer (via factory, directly in DB for setup)
        customer = create_customer(db_session, name="Integration Corp")

        # 2. Create assembly via HTTP
        create_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "IT-001",
                "assembly_name": "Integration Assembly",
                "lot_number": "LOT-INT",
                "ordered_qty": 1,
            },
            headers=boss_headers,
        )
        assert create_resp.status_code == 200, create_resp.text
        assembly = create_resp.json()
        assembly_id = assembly["id"]
        assert assembly["assembly_code"] == "IT-001"
        assert assembly["current_stage"] == "fabrication"

        # 3. Add parts via HTTP
        part1_resp = client.post(
            f"/api/v2/bom/assemblies/{assembly_id}/parts",
            json={
                "mark_number": "IT-001-01",
                "part_name": "Side Plate",
                "section": "PLATE",
                "total_qty": 4,
                "weight_per_unit_kg": 2.5,
            },
            headers=boss_headers,
        )
        assert part1_resp.status_code == 200, part1_resp.text
        part1 = part1_resp.json()
        assert part1["mark_number"] == "IT-001-01"
        assert part1["total_qty"] == 4
        assert part1["total_weight_kg"] == pytest.approx(10.0, abs=0.01)

        part2_resp = client.post(
            f"/api/v2/bom/assemblies/{assembly_id}/parts",
            json={
                "mark_number": "IT-001-02",
                "part_name": "Base Angle",
                "section": "ANGLE",
                "total_qty": 2,
                "weight_per_unit_kg": 1.5,
            },
            headers=boss_headers,
        )
        assert part2_resp.status_code == 200, part2_resp.text

        # 4. Get assembly detail — verify parts and weight
        detail_resp = client.get(
            f"/api/v2/bom/assemblies/{assembly_id}",
            headers=boss_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["parts"]) == 2
        # Weight: (4 * 2.5) + (2 * 1.5) = 10.0 + 3.0 = 13.0
        assert detail["estimated_weight_kg"] == pytest.approx(13.0, abs=0.01)

        # Stage tracking rows exist
        assert len(detail["stage_tracking"]) == 3
        fab_track = next(s for s in detail["stage_tracking"] if s["stage"] == "fabrication")
        # total_pieces = 4 + 2 = 6
        assert fab_track["total_pieces"] == 6

        # 5. Calculate material requirements
        calc_resp = client.post(
            f"/api/v2/bom/assemblies/{assembly_id}/calculate-materials",
            headers=boss_headers,
        )
        assert calc_resp.status_code == 200
        reqs = calc_resp.json()
        assert len(reqs) == 2  # PLATE + ANGLE
        names = sorted(r["material_name"] for r in reqs)
        assert names == ["ANGLE", "PLATE"]

        # 6. Update piece count (fabrication stage)
        piece_resp = client.put(
            f"/api/v2/bom/assemblies/{assembly_id}/stages/fabrication/pieces",
            json={"completed_delta": 3},
            headers=boss_headers,
        )
        assert piece_resp.status_code == 200
        piece_data = piece_resp.json()
        assert piece_data["completed_pieces"] == 3
        assert piece_data["status"] == "in_progress"

        # 7. Verify progress endpoint
        progress_resp = client.get(
            f"/api/v2/bom/assemblies/{assembly_id}/progress",
            headers=boss_headers,
        )
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress["assembly_id"] == assembly_id
        fab_progress = next(s for s in progress["stages"] if s["stage"] == "fabrication")
        assert fab_progress["completed_pieces"] == 3
        assert fab_progress["total_pieces"] == 6
        assert fab_progress["percentage"] == pytest.approx(50.0, abs=0.1)

    def test_assembly_not_found_returns_404(self, client, boss_headers):
        """GET /assemblies/99999 returns 404."""
        resp = client.get("/api/v2/bom/assemblies/99999", headers=boss_headers)
        assert resp.status_code == 404

    def test_add_part_to_nonexistent_assembly(self, client, boss_headers):
        """POST parts to a non-existent assembly returns 400."""
        resp = client.post(
            "/api/v2/bom/assemblies/99999/parts",
            json={
                "mark_number": "X-01",
                "part_name": "Ghost Part",
                "total_qty": 1,
            },
            headers=boss_headers,
        )
        assert resp.status_code == 400

    def test_delete_part_via_http(self, client, boss_headers, db_session):
        """DELETE a part and verify weight recalculation."""
        customer = create_customer(db_session, name="Delete Corp")

        # Create assembly with a part
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "DEL-001",
                "assembly_name": "Deletable",
                "parts": [
                    {
                        "mark_number": "D-01",
                        "part_name": "Remove Me",
                        "section": "PIPE",
                        "total_qty": 2,
                        "weight_per_unit_kg": 5.0,
                    },
                ],
            },
            headers=boss_headers,
        )
        assert asm_resp.status_code == 200
        asm = asm_resp.json()
        part_id = asm["parts"][0]["id"]

        # Delete the part
        del_resp = client.delete(
            f"/api/v2/bom/parts/{part_id}",
            headers=boss_headers,
        )
        assert del_resp.status_code == 200

        # Assembly weight should be 0
        detail = client.get(
            f"/api/v2/bom/assemblies/{asm['id']}",
            headers=boss_headers,
        ).json()
        assert detail["estimated_weight_kg"] == pytest.approx(0.0, abs=0.01)
        assert len(detail["parts"]) == 0


class TestProgressDashboardHttp:
    """Integration tests for the progress dashboard endpoint."""

    def test_progress_dashboard(self, client, boss_headers, db_session):
        """GET /api/v2/bom/progress-dashboard returns aggregated data."""
        customer = create_customer(db_session, name="Dashboard Corp")

        # Create assembly with parts
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "DASH-001",
                "assembly_name": "Dashboard Test",
                "parts": [
                    {
                        "mark_number": "D-01",
                        "part_name": "Part One",
                        "total_qty": 10,
                        "weight_per_unit_kg": 1.0,
                    },
                ],
            },
            headers=boss_headers,
        )
        assert asm_resp.status_code == 200

        resp = client.get("/api/v2/bom/progress-dashboard", headers=boss_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_assemblies"] >= 1
        assert "stages" in data
