"""
Smoke tests — verify that the test infrastructure itself works.

These tests exercise:
1. The in-memory test database (tables created, factories work)
2. The FastAPI TestClient with dependency overrides
3. Basic endpoint reachability
"""

from backend_core.app.models import User
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

    def test_boss_client_is_authenticated(self, db, boss_client):
        """Boss client can hit an auth-protected endpoint."""
        # Create a customer so the list endpoint has data
        create_test_customer(db, name="Auth Test Customer")
        resp = boss_client.get("/customers/")
        assert resp.status_code == 200

    def test_user_factory_persists_in_db(self, db):
        """A user created via factory is queryable from the same session."""
        user = create_test_user(db, username="persist_check", role="User")
        found = db.query(User).filter(User.username == "persist_check").first()
        assert found is not None
        assert found.id == user.id
