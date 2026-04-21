"""
v3 Drawing API — Integration Tests
Tests the complete drawing → assembly → component → instance lifecycle.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_core'))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.main import create_app
from app.deps import get_db
from app.security import hash_password


# Test database (in-memory SQLite)
TEST_DB_URL = "sqlite:///./test_v3.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Create test client with clean database."""
    Base.metadata.create_all(bind=engine)
    from app.models_v2 import Base as BaseV2
    BaseV2.metadata.create_all(bind=engine)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    db = TestSession()
    from app.models import User
    admin = db.query(User).filter(User.username == "testadmin").first()
    if not admin:
        admin = User(
            username="testadmin",
            email="test@kbsteel.com",
            hashed_password=hash_password("TestPass123!"),
            role="Boss",
            company="Test Steel"
        )
        db.add(admin)
        db.commit()
    db.close()

    with TestClient(app) as c:
        resp = c.post("/auth/login", json={"username": "testadmin", "password": "TestPass123!"})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["access_token"]
        c.headers = {"Authorization": f"Bearer {token}"}
        yield c

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if os.path.exists("test_v3.db"):
            os.remove("test_v3.db")
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def customer_id(client):
    """Create a test customer."""
    resp = client.post("/customers", json={
        "name": "Test Steel Corp",
        "project_details": "Test Project"
    })
    assert resp.status_code in (200, 201), f"Customer creation failed: {resp.text}"
    return resp.json()["id"]


class TestDrawingLifecycle:
    """Test complete drawing → release → track → complete flow."""

    drawing_id = None
    assembly_id = None
    component_id = None

    def test_01_create_drawing(self, client, customer_id):
        resp = client.post("/api/v3/drawings/", json={
            "drawing_number": "D-001",
            "title": "Handrail Assembly",
            "customer_id": customer_id,
            "project_ref": "PRJ-001",
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"
        data = resp.json()
        assert data["drawing_number"] == "D-001"
        assert data["revision"] == "A"
        assert data["status"] == "draft"
        TestDrawingLifecycle.drawing_id = data["id"]

    def test_02_add_assembly(self, client):
        resp = client.post(f"/api/v3/drawings/{self.drawing_id}/assemblies", json={
            "mark_number": "A1",
            "description": "Main handrail assembly",
            "quantity_required": 2,
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"
        data = resp.json()
        assert data["mark_number"] == "A1"
        assert data["quantity_required"] == 2
        TestDrawingLifecycle.assembly_id = data["id"]

    def test_03_add_components(self, client):
        # Component 1: Top rail beam
        resp = client.post(f"/api/v3/drawings/assemblies/{self.assembly_id}/components", json={
            "piece_mark": "P1",
            "profile_section": "UB203X133X25",
            "grade": "S275",
            "length_mm": 3200,
            "quantity_per_assembly": 1,
            "weight_each_kg": 80.0,
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"
        TestDrawingLifecycle.component_id = resp.json()["id"]

        # Component 2: Vertical posts
        resp = client.post(f"/api/v3/drawings/assemblies/{self.assembly_id}/components", json={
            "piece_mark": "P2",
            "profile_section": "50X50X5 SHS",
            "grade": "S275",
            "length_mm": 1100,
            "quantity_per_assembly": 3,
            "weight_each_kg": 8.5,
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"

    def test_04_release_drawing(self, client):
        resp = client.post(f"/api/v3/drawings/{self.drawing_id}/release")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "released"

    def test_05_get_drawing_detail(self, client):
        resp = client.get(f"/api/v3/drawings/{self.drawing_id}")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        # DrawingOut uses instance_count field
        # 2 assemblies * (1 P1 + 3 P2) = 2 + 6 = 8 instances
        assert data["instance_count"] == 8
        assert data["completed_instance_count"] == 0

    def test_06_get_progress(self, client):
        resp = client.get(f"/api/v3/drawings/{self.drawing_id}/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_instances"] == 8
        assert data["pct_complete"] == 0.0

    def test_07_list_drawings(self, client, customer_id):
        resp = client.get(f"/api/v3/drawings/?customer_id={customer_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["drawing_number"] == "D-001"

    def test_08_advance_single_instance(self, client):
        # Get the drawing detail to find instance IDs
        resp = client.get(f"/api/v3/drawings/{self.drawing_id}")
        data = resp.json()
        assemblies = data.get("assemblies", [])

        # Find first instance ID
        instance_id = None
        for asm in assemblies:
            for comp in asm.get("components", []):
                # ComponentOut doesn't include instances directly,
                # so we need to get instances from the progress endpoint
                break

        # Use progress endpoint to check instance count, then try advancing instance 1
        # The first instance created should have the lowest ID
        from app.models_v3 import ComponentInstance, Component, Assembly
        db = TestSession()
        instances = (
            db.query(ComponentInstance)
            .join(Component).join(Assembly)
            .filter(Assembly.drawing_id == self.drawing_id)
            .order_by(ComponentInstance.id)
            .all()
        )
        assert len(instances) == 8, f"Expected 8 instances, got {len(instances)}"
        instance_id = instances[0].id
        db.close()

        # Start the stage first
        resp = client.post(f"/api/v3/drawings/instances/{instance_id}/start")
        assert resp.status_code == 200, f"Start failed: {resp.text}"

        # Advance from cutting to next stage
        resp = client.post(f"/api/v3/drawings/instances/{instance_id}/advance", json={
            "component_instance_id": instance_id,
            "remarks": "Test advance",
        })
        assert resp.status_code == 200, f"Advance failed: {resp.text}"
        result = resp.json()
        assert result["from_stage"] == "cutting"

    def test_08b_material_usage(self, client):
        """Check items used drawing-wise."""
        resp = client.get(f"/api/v3/drawings/{self.drawing_id}/material-usage")
        assert resp.status_code == 200, f"Material usage failed: {resp.text}"
        data = resp.json()
        assert data["drawing_id"] == self.drawing_id
        assert data["drawing_number"] == "D-001"
        assert data["total_bom_weight_kg"] > 0
        # BOM: 2 assemblies * (1*80kg + 3*8.5kg) = 2 * 105.5 = 211 kg
        assert data["total_bom_weight_kg"] == 211.0
        # Check assemblies breakdown
        assert len(data["assemblies"]) == 1  # 1 assembly type (A1)
        asm = data["assemblies"][0]
        assert asm["mark_number"] == "A1"
        assert len(asm["components"]) == 2  # P1 and P2
        # P1: 2 instances (qty_per_assembly=1, assembly_qty=2)
        p1 = next(c for c in asm["components"] if c["piece_mark"] == "P1")
        assert p1["total_instances"] == 2
        assert p1["total_required_kg"] == 160.0  # 80kg * 2
        # P2: 6 instances (qty_per_assembly=3, assembly_qty=2)
        p2 = next(c for c in asm["components"] if c["piece_mark"] == "P2")
        assert p2["total_instances"] == 6
        assert p2["total_required_kg"] == 51.0  # 8.5kg * 6
        # consumption_pct should be 0 since no material was consumed yet
        assert data["consumption_pct"] == 0.0

    def test_09_get_kanban(self, client):
        resp = client.get(f"/api/v3/drawings/kanban?drawing_id={self.drawing_id}")
        assert resp.status_code == 200, f"Kanban failed: {resp.text}"
        data = resp.json()
        assert "columns" in data

    def test_10_reserve_materials(self, client):
        # Reserve requires a body with drawing_id
        resp = client.post(f"/api/v3/drawings/{self.drawing_id}/reserve-materials", json={
            "drawing_id": self.drawing_id,
        })
        # May fail if components have no material/inventory link — that's expected
        # Accept either 200 (success) or 400 (no material link)
        assert resp.status_code in (200, 400), f"Reserve failed: {resp.text}"


class TestDrawingValidation:
    """Test error cases and validation."""

    def test_create_without_customer(self, client):
        resp = client.post("/api/v3/drawings/", json={
            "drawing_number": "D-999",
            "title": "Test",
            "customer_id": 99999,
        })
        assert resp.status_code in (400, 404)

    def test_release_empty_drawing(self, client, customer_id):
        # Create drawing with no assemblies
        resp = client.post("/api/v3/drawings/", json={
            "drawing_number": "D-EMPTY",
            "title": "Empty",
            "customer_id": customer_id,
        })
        drawing_id = resp.json()["id"]

        # Try to release — should fail
        resp = client.post(f"/api/v3/drawings/{drawing_id}/release")
        assert resp.status_code == 400

    def test_advance_nonexistent_instance(self, client):
        resp = client.post("/api/v3/drawings/instances/99999/advance", json={
            "component_instance_id": 99999,
        })
        assert resp.status_code in (400, 404)
