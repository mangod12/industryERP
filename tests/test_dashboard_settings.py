"""
Tests for enhanced dashboard endpoint and system settings API.

Covers:
- Enhanced summary returns all 6 number cards with correct structure
- Company settings CRUD
- Naming series update
- System config CRUD
- Role enforcement (only Boss can update settings)
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so conftest helpers are importable
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend_core.app.models import (
    ScrapRecord,
)
from backend_core.app.models_v2 import (
    NumberSequence,
    SystemConfig,
)
from backend_core.app.models_v3 import StageConfig


def _create_customer(db, **kw):
    """Inline factory to avoid importing conftest."""
    from tests.conftest import create_test_customer

    return create_test_customer(db, **kw)


def _create_production_item(db, customer_id, **kw):
    from tests.conftest import create_test_production_item

    return create_test_production_item(db, customer_id, **kw)


def _create_inventory(db, **kw):
    from tests.conftest import create_test_inventory

    return create_test_inventory(db, **kw)


# =============================================================================
# ENHANCED DASHBOARD
# =============================================================================


class TestEnhancedDashboardSummary:
    """Tests for GET /dashboard/enhanced-summary."""

    def test_returns_six_number_cards(self, boss_client):
        """Enhanced summary must return exactly 6 number cards."""
        r = boss_client.get("/dashboard/enhanced-summary")
        assert r.status_code == 200
        data = r.json()
        assert "number_cards" in data
        assert len(data["number_cards"]) == 6

    def test_number_card_structure(self, boss_client):
        """Each number card has required keys: label, value, unit, badge."""
        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        required_keys = {"label", "value", "unit", "badge"}
        for card in data["number_cards"]:
            assert required_keys.issubset(card.keys()), (
                f"Card '{card.get('label')}' missing keys: {required_keys - set(card.keys())}"
            )

    def test_card_labels_are_correct(self, boss_client):
        """Verify the 6 expected card labels are present."""
        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        labels = [c["label"] for c in data["number_cards"]]
        expected = [
            "Total Stock Value",
            "Pending GRNs",
            "Open Dispatches",
            "Production Completion",
            "Scrap Rate",
            "Low Stock Alerts",
        ]
        assert labels == expected

    def test_recent_activity_key_present(self, boss_client):
        """Response includes recent_activity list."""
        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        assert "recent_activity" in data
        assert isinstance(data["recent_activity"], list)

    def test_production_completion_with_data(self, db, boss_client):
        """Production completion card shows correct percentage."""
        cust = _create_customer(db)
        # Create 4 items: 2 completed, 2 not
        for i in range(2):
            _create_production_item(
                db,
                cust.id,
                is_completed=True,
                current_stage="completed",
            )
        for i in range(2):
            _create_production_item(db, cust.id)

        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        completion_card = next(c for c in data["number_cards"] if c["label"] == "Production Completion")
        assert completion_card["value"] == 50.0
        assert completion_card["unit"] == "%"

    def test_low_stock_count(self, db, boss_client):
        """Low stock alerts card counts items below 15% remaining."""
        # Healthy stock
        _create_inventory(db, total=1000.0, used=0.0)
        # Low stock (used 900 of 1000 = 10% remaining)
        _create_inventory(db, total=1000.0, used=900.0)

        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        low_stock_card = next(c for c in data["number_cards"] if c["label"] == "Low Stock Alerts")
        assert low_stock_card["value"] >= 1
        assert low_stock_card["badge"] == "danger"

    def test_scrap_rate_badge(self, db, boss_client):
        """Scrap rate badge is 'danger' when rate > 5%."""
        # Create inventory with consumed material
        _create_inventory(db, total=100.0, used=50.0)
        # Create scrap that would be > 5% of consumed
        scrap = ScrapRecord(
            material_name="Steel Plate",
            weight_kg=10.0,
            reason_code="cutting_waste",
            created_by=1,
        )
        db.add(scrap)
        db.commit()

        r = boss_client.get("/dashboard/enhanced-summary")
        data = r.json()
        scrap_card = next(c for c in data["number_cards"] if c["label"] == "Scrap Rate")
        # 10 kg scrap / 50 kg consumed = 20% > 5%
        assert scrap_card["badge"] == "danger"

    def test_unauthenticated_returns_401(self, client):
        """Unauthenticated request returns 401."""
        r = client.get("/dashboard/enhanced-summary")
        assert r.status_code == 401


# =============================================================================
# COMPANY SETTINGS
# =============================================================================


class TestCompanySettings:
    """Tests for GET/PUT /api/v2/settings/company."""

    def test_get_company_settings_empty(self, boss_client):
        """GET returns all company keys with None when nothing is set."""
        r = boss_client.get("/api/v2/settings/company")
        assert r.status_code == 200
        data = r.json()
        assert "company_name" in data
        assert "company_gstin" in data

    def test_update_company_settings(self, boss_client):
        """PUT updates company settings."""
        r = boss_client.put(
            "/api/v2/settings/company",
            json={"company_name": "KB Steel Pvt Ltd", "company_gstin": "22AAAAA0000A1Z5"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "company_name" in body["updated"]

        # Verify it was persisted
        r2 = boss_client.get("/api/v2/settings/company")
        data = r2.json()
        assert data["company_name"] == "KB Steel Pvt Ltd"
        assert data["company_gstin"] == "22AAAAA0000A1Z5"

    def test_update_company_no_fields_returns_400(self, boss_client):
        """PUT with no fields returns 400."""
        r = boss_client.put("/api/v2/settings/company", json={})
        assert r.status_code == 400

    def test_non_boss_cannot_update_company(self, user_client):
        """Non-Boss user is forbidden from updating company settings."""
        r = user_client.put(
            "/api/v2/settings/company",
            json={"company_name": "Hacked"},
        )
        assert r.status_code == 403


# =============================================================================
# NAMING SERIES
# =============================================================================


class TestNamingSeries:
    """Tests for GET /api/v2/settings/naming-series and PUT .../naming-series/{name}."""

    def test_get_naming_series_empty(self, boss_client):
        """GET returns empty list when no sequences exist."""
        r = boss_client.get("/api/v2/settings/naming-series")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_naming_series_with_data(self, db, boss_client):
        """GET returns sequences when data exists."""
        seq = NumberSequence(
            sequence_name="grn",
            prefix="GRN",
            current_number=42,
            padding=6,
            format_str="{prefix}/{fy}/{####}",
        )
        db.add(seq)
        db.commit()

        r = boss_client.get("/api/v2/settings/naming-series")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        grn_seq = next(s for s in data if s["sequence_name"] == "grn")
        assert grn_seq["prefix"] == "GRN"
        assert grn_seq["current_number"] == 42

    def test_update_naming_series(self, db, boss_client):
        """PUT updates the format_str of a sequence."""
        seq = NumberSequence(
            sequence_name="dispatch",
            prefix="DSP",
            current_number=1,
            padding=5,
            format_str="DSP-{####}",
        )
        db.add(seq)
        db.commit()

        r = boss_client.put(
            "/api/v2/settings/naming-series/dispatch",
            json={"format_str": "DSP/{fy}/{#####}"},
        )
        assert r.status_code == 200
        assert r.json()["format_str"] == "DSP/{fy}/{#####}"

    def test_update_naming_series_not_found(self, boss_client):
        """PUT on non-existent sequence returns 404."""
        r = boss_client.put(
            "/api/v2/settings/naming-series/nonexistent",
            json={"format_str": "X"},
        )
        assert r.status_code == 404

    def test_non_boss_cannot_update_naming_series(self, db, user_client):
        """Non-Boss user is forbidden from updating naming series."""
        r = user_client.put(
            "/api/v2/settings/naming-series/grn",
            json={"format_str": "X"},
        )
        assert r.status_code == 403


# =============================================================================
# SYSTEM CONFIG
# =============================================================================


class TestSystemConfig:
    """Tests for GET /api/v2/settings/system and PUT .../system/{key}."""

    def test_get_system_config_empty(self, boss_client):
        """GET returns empty list when nothing configured."""
        r = boss_client.get("/api/v2/settings/system")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_read_system_config(self, boss_client):
        """PUT creates a new config, GET returns it."""
        r = boss_client.put(
            "/api/v2/settings/system/default_currency",
            json={"value": "INR"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

        r2 = boss_client.get("/api/v2/settings/system")
        data = r2.json()
        keys = [c["key"] for c in data]
        assert "default_currency" in keys
        cfg = next(c for c in data if c["key"] == "default_currency")
        assert cfg["value"] == "INR"

    def test_update_existing_system_config(self, db, boss_client):
        """PUT updates an existing config value."""
        cfg = SystemConfig(key="theme", value="light")
        db.add(cfg)
        db.commit()

        r = boss_client.put(
            "/api/v2/settings/system/theme",
            json={"value": "dark"},
        )
        assert r.status_code == 200
        assert r.json()["value"] == "dark"

    def test_non_boss_cannot_update_system_config(self, user_client):
        """Non-Boss user is forbidden from updating system config."""
        r = user_client.put(
            "/api/v2/settings/system/any_key",
            json={"value": "val"},
        )
        assert r.status_code == 403

    def test_non_boss_can_read_system_config(self, user_client):
        """Any authenticated user can read system config."""
        r = user_client.get("/api/v2/settings/system")
        assert r.status_code == 200


# =============================================================================
# WORKFLOWS (read-only)
# =============================================================================


class TestWorkflowConfigs:
    """Tests for GET /api/v2/settings/workflows."""

    def test_get_workflows_empty(self, boss_client):
        """GET returns empty list when no custom configs."""
        r = boss_client.get("/api/v2/settings/workflows")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_workflows_with_data(self, db, boss_client):
        """GET returns stage configs when data exists."""
        cfg = StageConfig(
            stage_name="cutting",
            sequence=1,
            is_mandatory=True,
            auto_deduct_material=True,
        )
        db.add(cfg)
        db.commit()

        r = boss_client.get("/api/v2/settings/workflows")
        data = r.json()
        assert len(data) >= 1
        assert data[0]["stage_name"] == "cutting"


# =============================================================================
# ROLE ENFORCEMENT
# =============================================================================


class TestRoleEnforcement:
    """Verify that all write endpoints require Boss role."""

    WRITE_ENDPOINTS = [
        ("PUT", "/api/v2/settings/company", {"company_name": "X"}),
        ("PUT", "/api/v2/settings/naming-series/grn", {"format_str": "X"}),
        ("PUT", "/api/v2/settings/system/key", {"value": "X"}),
    ]

    @pytest.mark.parametrize("method,path,payload", WRITE_ENDPOINTS)
    def test_user_role_forbidden(self, user_client, method, path, payload):
        """User role gets 403 on all write endpoints."""
        if method == "PUT":
            r = user_client.put(path, json=payload)
        assert r.status_code == 403

    @pytest.mark.parametrize("method,path,payload", WRITE_ENDPOINTS)
    def test_boss_role_allowed(self, boss_client, method, path, payload):
        """Boss role is allowed on all write endpoints (even if resource not found)."""
        if method == "PUT":
            r = boss_client.put(path, json=payload)
        # 200 or 400 or 404 are acceptable (not 403)
        assert r.status_code != 403
