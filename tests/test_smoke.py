"""
Smoke tests — verify that the test infrastructure itself works.

These tests exercise:
1. The in-memory test database (tables created, factories work)
2. The FastAPI TestClient with dependency overrides
3. Basic endpoint reachability
"""

from decimal import Decimal

from backend_core.app.models import User
from backend_core.app.models_v2 import MovementType, StockMovement, StorageLocation, Vendor
from tests.conftest import (
    create_test_customer,
    create_test_inventory,
    create_test_production_item,
    create_test_stock_lot,
    create_test_user,
)

# ---------------------------------------------------------------------------
# Database & factory smoke tests
# ---------------------------------------------------------------------------


class TestDatabaseSetup:
    """Verify the in-memory DB and session fixture work."""

    def test_session_is_functional(self, db):
        """The db fixture yields a usable SQLAlchemy session."""
        assert db is not None
        # Simple round-trip: write and read back
        user = create_test_user(db, role="Boss")
        fetched = db.get(User, user.id)
        assert fetched is not None
        assert fetched.username == user.username

    def test_tables_are_isolated_between_tests(self, db):
        """Each test gets a fresh database — no leftover rows."""
        count = db.query(User).count()
        assert count == 0, f"Expected 0 users in fresh db, got {count}"


class TestFactories:
    """Verify each factory produces valid ORM objects."""

    def test_create_test_user(self, db):
        user = create_test_user(db, role="Store Keeper")
        assert user.id is not None
        assert user.role == "Store Keeper"
        assert user.is_active is True

    def test_create_test_customer(self, db):
        customer = create_test_customer(db, name="Acme Steel")
        assert customer.id is not None
        assert customer.name == "Acme Steel"
        assert customer.order_status == "ACTIVE"

    def test_create_test_production_item(self, db):
        customer = create_test_customer(db)
        item = create_test_production_item(db, customer.id)
        assert item.id is not None
        assert item.customer_id == customer.id
        assert item.current_stage == "fabrication"

    def test_create_test_inventory(self, db):
        inv = create_test_inventory(db, name="HR Coil 2.5mm")
        assert inv.id is not None
        assert inv.name == "HR Coil 2.5mm"
        assert inv.total == 1000.0

    def test_create_test_stock_lot(self, db):
        lot = create_test_stock_lot(db)
        assert lot.id is not None
        assert lot.lot_number is not None
        assert lot.material_id is not None
        assert float(lot.current_weight_kg) > 0


# ---------------------------------------------------------------------------
# TestClient smoke tests
# ---------------------------------------------------------------------------


class TestClientSetup:
    """Verify TestClient and dependency overrides."""

    def test_sanity_endpoint(self, boss_client):
        """The /test-sanity endpoint returns 200 with {status: ok}."""
        resp = boss_client.get("/test-sanity")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_version_endpoint(self, boss_client):
        """The /version endpoint returns version info."""
        resp = boss_client.get("/version")
        assert resp.status_code == 200
        body = resp.json()
        assert "version" in body
        assert "app" in body

    def test_healthz_endpoint(self, boss_client):
        """The production health endpoint returns a stable lightweight status."""
        resp = boss_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_boss_client_is_authenticated(self, db, boss_client):
        """Boss client can hit an auth-protected endpoint."""
        # Create a customer so the list endpoint has data
        create_test_customer(db, name="Auth Test Customer")
        resp = boss_client.get("/customers/")
        assert resp.status_code == 200

    def test_storage_locations_endpoint_lists_active_locations(self, db, boss_client):
        """GRN approval needs a selectable active yard/rack list."""
        db.add_all(
            [
                StorageLocation(code="A-YARD", name="A Yard", location_type="yard", is_active=True),
                StorageLocation(code="B-RACK", name="B Rack", location_type="rack", is_active=True),
                StorageLocation(code="Z-OLD", name="Old Yard", location_type="yard", is_active=False),
            ]
        )
        db.commit()

        resp = boss_client.get("/api/v2/inventory/locations")

        assert resp.status_code == 200
        body = resp.json()
        assert [item["code"] for item in body] == ["A-YARD", "B-RACK"]
        assert body[0]["name"] == "A Yard"

    def test_stock_lot_movements_endpoint_uses_existing_user_display_field(self, db, boss_client):
        """Movement history must use a real user display field."""
        user = db.query(User).filter(User.username == "boss_test").one()
        lot = create_test_stock_lot(db)
        movement = StockMovement(
            movement_number="MOV-SMOKE-001",
            stock_lot_id=lot.id,
            movement_type=MovementType.ADJUSTMENT_PLUS,
            weight_change_kg=Decimal("5.000"),
            weight_before_kg=Decimal("100.000"),
            weight_after_kg=Decimal("105.000"),
            reason="Smoke test adjustment",
            created_by=user.id,
        )
        db.add(movement)
        db.commit()

        resp = boss_client.get(f"/api/v2/inventory/movements/{lot.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["movement_number"] == "MOV-SMOKE-001"
        assert body[0]["created_by_name"] == "boss_test"

    def test_grn_detail_endpoint_reads_created_grn(self, db, boss_client):
        """The GRN page detail modal requires a read-by-id endpoint."""
        vendor = Vendor(code="V-GRN-READ", name="GRN Read Vendor")
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        create_resp = boss_client.post("/api/v2/grn/", json={"vendor_id": vendor.id, "vehicle_number": "MH12AB1234"})
        assert create_resp.status_code == 201
        grn_id = create_resp.json()["grn_id"]

        detail_resp = boss_client.get(f"/api/v2/grn/{grn_id}")

        assert detail_resp.status_code == 200
        body = detail_resp.json()
        assert body["id"] == grn_id
        assert body["vendor_name"] == "GRN Read Vendor"
        assert body["line_items"] == []

    def test_dispatch_detail_endpoint_reads_created_dispatch(self, db, boss_client):
        """The dispatch page detail modal requires a read-by-id endpoint."""
        customer = create_test_customer(db, name="Dispatch Read Customer")

        create_resp = boss_client.post(
            "/api/v2/dispatch/", json={"customer_id": customer.id, "vehicle_number": "MH12AB5678"}
        )
        assert create_resp.status_code == 201
        dispatch_id = create_resp.json()["dispatch_id"]

        detail_resp = boss_client.get(f"/api/v2/dispatch/{dispatch_id}")

        assert detail_resp.status_code == 200
        body = detail_resp.json()
        assert body["id"] == dispatch_id
        assert body["customer_name"] == "Dispatch Read Customer"
        assert body["line_items"] == []

    def test_role_notification_settings_require_auth(self, client):
        """Role notification preferences are not public metadata."""
        resp = client.get("/notifications/roles/Boss")
        assert resp.status_code == 401

    def test_user_factory_persists_in_db(self, db):
        """A user created via factory is queryable from the same session."""
        user = create_test_user(db, username="persist_check", role="User")
        found = db.query(User).filter(User.username == "persist_check").first()
        assert found is not None
        assert found.id == user.id

    def test_production_cors_requires_explicit_origins(self, monkeypatch):
        """Production mode must not silently fall back to development CORS origins."""
        from backend_core.app.main import get_cors_origins

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        try:
            get_cors_origins()
        except RuntimeError as exc:
            assert "CORS_ORIGINS" in str(exc)
        else:
            raise AssertionError("production mode accepted implicit CORS origins")
