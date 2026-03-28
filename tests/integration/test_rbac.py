"""
Integration tests for Role-Based Access Control (RBAC).

Verifies that:
  - Read-only users (role "User") can view but not create/modify resources
  - Boss users have full access to BOM and tracking endpoints
  - Unauthorized users get 403 on protected endpoints
"""
import pytest

from tests.factories import create_customer, create_assembly, create_assembly_part


# ---------------------------------------------------------------------------
# BOM Assembly RBAC
# ---------------------------------------------------------------------------


class TestBomRbac:
    """Permission enforcement on /api/v2/bom/ endpoints."""

    def test_readonly_user_cannot_create_assembly(
        self, client, readonly_headers, db_session
    ):
        """User with role 'User' gets 403 on POST /assemblies."""
        customer = create_customer(db_session, name="RBAC Corp")
        resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "RBAC-001",
                "assembly_name": "Forbidden Assembly",
            },
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_boss_can_create_assembly(self, client, boss_headers, db_session):
        """Boss role can create assemblies successfully."""
        customer = create_customer(db_session, name="Boss Corp")
        resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "BOSS-001",
                "assembly_name": "Boss Assembly",
            },
            headers=boss_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["assembly_code"] == "BOSS-001"

    def test_supervisor_can_create_assembly(
        self, client, supervisor_headers, db_session
    ):
        """Software Supervisor role can also create assemblies."""
        customer = create_customer(db_session, name="Sup Corp")
        resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "SUP-001",
                "assembly_name": "Supervisor Assembly",
            },
            headers=supervisor_headers,
        )
        assert resp.status_code == 200

    def test_user_can_view_assemblies(self, client, readonly_headers):
        """Any authenticated user can list assemblies (GET is read-only)."""
        resp = client.get("/api/v2/bom/assemblies", headers=readonly_headers)
        assert resp.status_code == 200

    def test_user_can_view_assembly_detail(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """Readonly user can view a specific assembly detail."""
        customer = create_customer(db_session, name="View Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "VIEW-001",
                "assembly_name": "Viewable Assembly",
            },
            headers=boss_headers,
        )
        asm_id = asm_resp.json()["id"]

        detail_resp = client.get(
            f"/api/v2/bom/assemblies/{asm_id}",
            headers=readonly_headers,
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["assembly_code"] == "VIEW-001"

    def test_readonly_user_cannot_add_part(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """User role cannot add parts to an assembly."""
        customer = create_customer(db_session, name="Part RBAC Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "PRBAC-001",
                "assembly_name": "Part Denied",
            },
            headers=boss_headers,
        )
        asm_id = asm_resp.json()["id"]

        resp = client.post(
            f"/api/v2/bom/assemblies/{asm_id}/parts",
            json={
                "mark_number": "DENY-01",
                "part_name": "Denied Part",
                "total_qty": 1,
            },
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_readonly_user_cannot_delete_part(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """User role cannot delete parts."""
        customer = create_customer(db_session, name="Del RBAC Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "DRBAC-001",
                "assembly_name": "Delete Denied",
                "parts": [
                    {
                        "mark_number": "DD-01",
                        "part_name": "Protected Part",
                        "total_qty": 1,
                        "weight_per_unit_kg": 1.0,
                    },
                ],
            },
            headers=boss_headers,
        )
        part_id = asm_resp.json()["parts"][0]["id"]

        resp = client.delete(
            f"/api/v2/bom/parts/{part_id}",
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_readonly_user_cannot_calculate_materials(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """User role cannot trigger material calculation."""
        customer = create_customer(db_session, name="Calc RBAC Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "CRBAC-001",
                "assembly_name": "Calc Denied",
            },
            headers=boss_headers,
        )
        asm_id = asm_resp.json()["id"]

        resp = client.post(
            f"/api/v2/bom/assemblies/{asm_id}/calculate-materials",
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_user_can_view_progress(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """Any authenticated user can view assembly progress."""
        customer = create_customer(db_session, name="Prog RBAC Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "PROG-001",
                "assembly_name": "Progress Viewable",
                "parts": [
                    {
                        "mark_number": "PV-01",
                        "part_name": "Viewable Part",
                        "total_qty": 5,
                        "weight_per_unit_kg": 1.0,
                    },
                ],
            },
            headers=boss_headers,
        )
        asm_id = asm_resp.json()["id"]

        resp = client.get(
            f"/api/v2/bom/assemblies/{asm_id}/progress",
            headers=readonly_headers,
        )
        assert resp.status_code == 200

    def test_user_can_view_dashboard(self, client, readonly_headers):
        """Any authenticated user can view the progress dashboard."""
        resp = client.get("/api/v2/bom/progress-dashboard", headers=readonly_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Stage Tracking RBAC
# ---------------------------------------------------------------------------


class TestTrackingRbac:
    """Permission enforcement on /tracking/ endpoints."""

    def test_readonly_user_cannot_start_stage(
        self, client, readonly_headers, db_session
    ):
        """User role cannot start a tracking stage."""
        customer = create_customer(db_session, name="Stage RBAC Corp")
        from tests.factories import create_production_item

        item = create_production_item(db_session, customer_id=customer.id)
        resp = client.post(
            "/tracking/start-stage",
            json={"production_item_id": item.id, "stage": "fabrication"},
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_readonly_user_cannot_complete_stage(
        self, client, readonly_headers, db_session
    ):
        """User role cannot complete a tracking stage."""
        customer = create_customer(db_session, name="Complete RBAC Corp")
        from tests.factories import create_production_item

        item = create_production_item(db_session, customer_id=customer.id)
        resp = client.post(
            "/tracking/complete-stage",
            json={"production_item_id": item.id, "stage": "fabrication"},
            headers=readonly_headers,
        )
        assert resp.status_code == 403

    def test_readonly_user_cannot_update_pieces(
        self, client, boss_headers, readonly_headers, db_session
    ):
        """User role cannot update piece counts on BOM stage tracking."""
        customer = create_customer(db_session, name="Pieces RBAC Corp")
        asm_resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": customer.id,
                "assembly_code": "PIECE-RBAC",
                "assembly_name": "Piece Denied",
                "parts": [
                    {
                        "mark_number": "PR-01",
                        "part_name": "Piece Part",
                        "total_qty": 5,
                        "weight_per_unit_kg": 1.0,
                    },
                ],
            },
            headers=boss_headers,
        )
        asm_id = asm_resp.json()["id"]

        resp = client.put(
            f"/api/v2/bom/assemblies/{asm_id}/stages/fabrication/pieces",
            json={"completed_delta": 1},
            headers=readonly_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


class TestUnauthenticated:
    """Requests without a token should be rejected."""

    def test_no_token_on_assemblies(self, client):
        """GET /assemblies without auth token returns 401."""
        resp = client.get("/api/v2/bom/assemblies")
        assert resp.status_code == 401

    def test_no_token_on_create(self, client):
        """POST /assemblies without auth token returns 401."""
        resp = client.post(
            "/api/v2/bom/assemblies",
            json={
                "customer_id": 1,
                "assembly_code": "NO-AUTH",
                "assembly_name": "No Auth",
            },
        )
        assert resp.status_code == 401

    def test_no_token_on_tracking(self, client):
        """POST /tracking/start-stage without auth token returns 401."""
        resp = client.post(
            "/tracking/start-stage",
            json={"production_item_id": 1, "stage": "fabrication"},
        )
        assert resp.status_code == 401
