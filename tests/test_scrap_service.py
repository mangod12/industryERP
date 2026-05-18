"""
Characterization tests for scrap service.

Tests scrap CRUD, reusable stock operations, analytics, bulk actions,
and CSV import — all via HTTP endpoints to verify the API contract is preserved
after extracting business logic into ScrapService.
"""

import pytest

from tests.conftest import create_test_inventory, create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_scrap_via_api(client, **overrides):
    """Helper to create a scrap record through the API."""
    payload = {
        "material_name": "ISMC 200",
        "weight_kg": 25.5,
        "reason_code": "cutting_waste",
        "quantity": 1,
    }
    payload.update(overrides)
    return client.post("/scrap/records", json=payload)


def _create_reusable_via_api(client, **overrides):
    """Helper to create a reusable stock item through the API."""
    payload = {
        "material_name": "ISMC 200",
        "dimensions": "1200mm x 150mm",
        "weight_kg": 18.0,
        "length_mm": 1200,
        "width_mm": 150,
        "quantity": 1,
        "quality_grade": "A",
    }
    payload.update(overrides)
    return client.post("/scrap/reusable", json=payload)


# ===========================================================================
# Scrap Record CRUD
# ===========================================================================


class TestCreateScrapRecord:
    def test_create_basic(self, boss_client):
        resp = _create_scrap_via_api(boss_client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["material_name"] == "ISMC 200"
        assert body["weight_kg"] == 25.5
        assert body["reason_code"] == "cutting_waste"
        assert body["status"] == "pending"
        assert body["id"] is not None

    def test_create_with_all_fields(self, boss_client):
        resp = _create_scrap_via_api(
            boss_client,
            length_mm=3000,
            width_mm=200,
            dimensions="3000mm x 200mm",
            notes="Test offcut",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["length_mm"] == 3000
        assert body["width_mm"] == 200
        assert body["dimensions"] == "3000mm x 200mm"
        assert body["notes"] == "Test offcut"

    def test_create_negative_weight_rejected(self, boss_client):
        resp = _create_scrap_via_api(boss_client, weight_kg=-5)
        assert resp.status_code == 400
        assert "positive" in resp.json()["detail"].lower()

    def test_create_zero_weight_rejected(self, boss_client):
        resp = _create_scrap_via_api(boss_client, weight_kg=0)
        assert resp.status_code == 400


class TestListScrapRecords:
    def test_list_empty(self, boss_client):
        resp = boss_client.get("/scrap/records")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created(self, boss_client):
        _create_scrap_via_api(boss_client)
        _create_scrap_via_api(boss_client, material_name="ISMB 300")
        resp = boss_client.get("/scrap/records")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_by_status(self, boss_client):
        _create_scrap_via_api(boss_client)
        resp = boss_client.get("/scrap/records?status=pending")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = boss_client.get("/scrap/records?status=disposed")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_filter_by_reason_code(self, boss_client):
        _create_scrap_via_api(boss_client, reason_code="defect")
        _create_scrap_via_api(boss_client, reason_code="damage")
        resp = boss_client.get("/scrap/records?reason_code=defect")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["reason_code"] == "defect"

    def test_filter_by_material_name(self, boss_client):
        _create_scrap_via_api(boss_client, material_name="ISMC 200")
        _create_scrap_via_api(boss_client, material_name="ISMB 300")
        resp = boss_client.get("/scrap/records?material_name=ISMB")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_trailing_slash_works(self, boss_client):
        resp = boss_client.get("/scrap/records/")
        assert resp.status_code == 200


class TestUpdateScrapStatus:
    def test_update_to_valid_status(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/status?status=disposed")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disposed"

    def test_update_with_scrap_value(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/status?status=sold&scrap_value=500")
        assert resp.status_code == 200

    def test_update_invalid_status_rejected(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/status?status=invalid_status")
        assert resp.status_code == 400

    def test_update_nonexistent_record(self, boss_client):
        resp = boss_client.put("/scrap/records/99999/status?status=disposed")
        assert resp.status_code == 404


class TestReturnScrapToInventory:
    def test_return_creates_inventory(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/return-to-inventory")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Returned to inventory"
        assert body["inventory_id"] is not None

    def test_return_adds_to_existing_inventory(self, boss_client, db):
        create_test_inventory(db, name="ISMC 200", total=100.0)
        create_resp = _create_scrap_via_api(boss_client, material_name="ISMC 200")
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/return-to-inventory")
        assert resp.status_code == 200

    def test_double_return_rejected(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        boss_client.put(f"/scrap/records/{rid}/return-to-inventory")
        resp = boss_client.put(f"/scrap/records/{rid}/return-to-inventory")
        assert resp.status_code == 400
        assert "Already returned" in resp.json()["detail"]

    def test_return_nonexistent(self, boss_client):
        resp = boss_client.put("/scrap/records/99999/return-to-inventory")
        assert resp.status_code == 404


class TestMoveToReusable:
    def test_move_basic(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client, dimensions="1200mm x 150mm")
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/move-to-reusable")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reusable_id"] is not None
        assert body["material"] == "ISMC 200"

    def test_move_with_quality_grade(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client, dimensions="1200mm x 150mm")
        rid = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/records/{rid}/move-to-reusable?quality_grade=B")
        assert resp.status_code == 200

    def test_move_nonexistent(self, boss_client):
        resp = boss_client.put("/scrap/records/99999/move-to-reusable")
        assert resp.status_code == 404


class TestDeleteScrapRecord:
    def test_delete_existing(self, boss_client):
        create_resp = _create_scrap_via_api(boss_client)
        rid = create_resp.json()["id"]
        resp = boss_client.delete(f"/scrap/records/{rid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == rid

    def test_delete_nonexistent(self, boss_client):
        resp = boss_client.delete("/scrap/records/99999")
        assert resp.status_code == 404


# ===========================================================================
# Reusable Stock
# ===========================================================================


class TestReusableStockCRUD:
    def test_create_reusable(self, boss_client):
        resp = _create_reusable_via_api(boss_client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["material_name"] == "ISMC 200"
        assert body["is_available"] is True

    def test_create_negative_weight(self, boss_client):
        resp = _create_reusable_via_api(boss_client, weight_kg=-1)
        assert resp.status_code == 400

    def test_list_reusable(self, boss_client):
        _create_reusable_via_api(boss_client)
        resp = boss_client.get("/scrap/reusable")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_filter_available_only(self, boss_client):
        _create_reusable_via_api(boss_client)
        resp = boss_client.get("/scrap/reusable?available_only=true")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_use_reusable(self, boss_client, db):
        from tests.conftest import create_test_customer, create_test_production_item

        customer = create_test_customer(db)
        item = create_test_production_item(db, customer.id)
        create_resp = _create_reusable_via_api(boss_client)
        stock_id = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/reusable/{stock_id}/use?production_item_id={item.id}")
        assert resp.status_code == 200

    def test_use_already_used_rejected(self, boss_client, db):
        from tests.conftest import create_test_customer, create_test_production_item

        customer = create_test_customer(db)
        item = create_test_production_item(db, customer.id)
        create_resp = _create_reusable_via_api(boss_client)
        stock_id = create_resp.json()["id"]
        boss_client.put(f"/scrap/reusable/{stock_id}/use?production_item_id={item.id}")
        resp = boss_client.put(f"/scrap/reusable/{stock_id}/use?production_item_id={item.id}")
        assert resp.status_code == 400

    def test_delete_reusable(self, boss_client):
        create_resp = _create_reusable_via_api(boss_client)
        stock_id = create_resp.json()["id"]
        resp = boss_client.delete(f"/scrap/reusable/{stock_id}")
        assert resp.status_code == 200

    def test_return_reusable_to_inventory(self, boss_client):
        create_resp = _create_reusable_via_api(boss_client)
        stock_id = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/reusable/{stock_id}/return-to-inventory")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Returned to main inventory"

    def test_mark_reusable_as_scrap(self, boss_client):
        create_resp = _create_reusable_via_api(boss_client)
        stock_id = create_resp.json()["id"]
        resp = boss_client.put(f"/scrap/reusable/{stock_id}/mark-scrap?reason=rusty")
        assert resp.status_code == 200
        assert resp.json()["scrap_id"] is not None


class TestFindMatchingReusable:
    def test_find_match(self, boss_client):
        _create_reusable_via_api(boss_client, length_mm=1200)
        resp = boss_client.get("/scrap/reusable/find-match?material_name=ISMC&required_length_mm=1100")
        assert resp.status_code == 200
        body = resp.json()
        assert body["required_length_mm"] == 1100
        assert len(body["matches"]) == 1

    def test_find_no_match(self, boss_client):
        resp = boss_client.get("/scrap/reusable/find-match?material_name=NONEXISTENT&required_length_mm=5000")
        assert resp.status_code == 200
        assert len(resp.json()["matches"]) == 0


# ===========================================================================
# Analytics and Summary
# ===========================================================================


class TestScrapAnalytics:
    def test_analytics_empty_db(self, boss_client):
        resp = boss_client.get("/scrap/analytics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["period_days"] == 30
        assert body["total_scrap_kg"] == 0
        assert "scrap_by_reason" in body
        assert "estimated_loss_value" in body

    def test_analytics_with_data(self, boss_client):
        _create_scrap_via_api(boss_client, weight_kg=100, reason_code="defect")
        _create_scrap_via_api(boss_client, weight_kg=50, reason_code="cutting_waste")
        resp = boss_client.get("/scrap/analytics?days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_scrap_kg"] == 150.0
        assert "defect" in body["scrap_by_reason"]

    def test_analytics_estimated_loss(self, boss_client):
        _create_scrap_via_api(boss_client, weight_kg=10)
        resp = boss_client.get("/scrap/analytics")
        body = resp.json()
        # 10 kg * DEFAULT_SCRAP_RATE_PER_KG (50) = 500
        assert body["estimated_loss_value"] == 500.0


class TestScrapSummary:
    def test_summary_empty(self, boss_client):
        resp = boss_client.get("/scrap/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scrap_total_kg"] == 0
        assert body["scrap_records_count"] == 0
        assert body["reusable_items_count"] == 0

    def test_summary_with_data(self, boss_client):
        _create_scrap_via_api(boss_client, weight_kg=30)
        _create_scrap_via_api(boss_client, weight_kg=20)
        _create_reusable_via_api(boss_client, weight_kg=15)
        resp = boss_client.get("/scrap/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scrap_total_kg"] == 50.0
        assert body["scrap_records_count"] == 2
        assert body["reusable_available_kg"] == 15.0
        assert body["reusable_items_count"] == 1


# ===========================================================================
# Bulk Actions
# ===========================================================================


class TestBulkAction:
    def test_bulk_dispose(self, boss_client):
        r1 = _create_scrap_via_api(boss_client).json()["id"]
        r2 = _create_scrap_via_api(boss_client).json()["id"]
        resp = boss_client.post(
            "/scrap/bulk-action?action=dispose",
            json=[r1, r2],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) == 2

    def test_bulk_return_to_inventory(self, boss_client):
        r1 = _create_scrap_via_api(boss_client).json()["id"]
        resp = boss_client.post(
            "/scrap/bulk-action?action=return_to_inventory",
            json=[r1],
        )
        assert resp.status_code == 200

    def test_bulk_mark_reusable(self, boss_client):
        r1 = _create_scrap_via_api(boss_client, dimensions="500mm x 100mm").json()["id"]
        resp = boss_client.post(
            "/scrap/bulk-action?action=mark_reusable",
            json=[r1],
        )
        assert resp.status_code == 200

    def test_bulk_no_records(self, boss_client):
        resp = boss_client.post(
            "/scrap/bulk-action?action=dispose",
            json=[99999],
        )
        assert resp.status_code == 404


# ===========================================================================
# CSV Upload
# ===========================================================================


class TestCSVUpload:
    def test_upload_csv(self, boss_client):
        csv_content = (
            "material_name,weight_kg,quantity,reason_code,dimensions\n"
            "ISMC 200,25.5,2,cutting_waste,200mm x 100mm\n"
            "ISMB 300,30.0,1,defect,300mm x 150mm\n"
        )
        resp = boss_client.post(
            "/scrap/upload-csv",
            files={"file": ("scrap.csv", csv_content.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["records_count"] == 2
        assert body["total_weight_kg"] > 0

    def test_upload_csv_with_aliases(self, boss_client):
        csv_content = "material,weight,qty,reason,dimension\nISMC 200,25.5,2,cutting_waste,200mm x 100mm\n"
        resp = boss_client.post(
            "/scrap/upload-csv",
            files={"file": ("scrap.csv", csv_content.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["records_count"] == 1

    def test_upload_missing_columns(self, boss_client):
        csv_content = "foo,bar\n1,2\n"
        resp = boss_client.post(
            "/scrap/upload-csv",
            files={"file": ("scrap.csv", csv_content.encode(), "text/csv")},
        )
        assert resp.status_code == 400
        assert "Missing columns" in resp.json()["detail"]

    def test_upload_invalid_extension(self, boss_client):
        resp = boss_client.post(
            "/scrap/upload-csv",
            files={"file": ("scrap.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400


# ===========================================================================
# Direct service-layer unit tests (no HTTP)
# ===========================================================================


class TestScrapServiceDirect:
    """Test service methods directly with a DB session (no HTTP overhead)."""

    def test_create_and_list(self, db):
        user = create_test_user(db, role="Boss")
        from backend_core.app.services.scrap_service import ScrapService

        record = ScrapService.create_scrap_record(
            db,
            material_name="Angle 50x50",
            weight_kg=12.0,
            reason_code="leftover",
            user_id=user.id,
        )
        assert record.id is not None
        assert record.status == "pending"

        records = ScrapService.list_scrap_records(db, status="pending")
        assert len(records) == 1

    def test_update_status(self, db):
        user = create_test_user(db, role="Boss")
        from backend_core.app.services.scrap_service import ScrapService

        record = ScrapService.create_scrap_record(
            db, material_name="Plate", weight_kg=50, reason_code="damage", user_id=user.id
        )
        result = ScrapService.update_scrap_status(db, record.id, "disposed")
        assert result["status"] == "disposed"

    def test_update_status_invalid(self, db):
        user = create_test_user(db, role="Boss")
        from backend_core.app.services.scrap_service import ScrapService

        record = ScrapService.create_scrap_record(
            db, material_name="Plate", weight_kg=50, reason_code="damage", user_id=user.id
        )
        with pytest.raises(ValueError):
            ScrapService.update_scrap_status(db, record.id, "bogus")

    def test_update_status_not_found(self, db):
        from backend_core.app.services.scrap_service import ScrapService

        with pytest.raises(LookupError):
            ScrapService.update_scrap_status(db, 99999, "disposed")

    def test_delete_not_found(self, db):
        from backend_core.app.services.scrap_service import ScrapService

        with pytest.raises(LookupError):
            ScrapService.delete_scrap_record(db, 99999)

    def test_return_to_inventory_not_found(self, db):
        from backend_core.app.services.scrap_service import ScrapService

        with pytest.raises(LookupError):
            ScrapService.return_to_inventory(db, 99999)

    def test_move_to_reusable_not_found(self, db):
        from backend_core.app.services.scrap_service import ScrapService

        with pytest.raises(LookupError):
            ScrapService.move_to_reusable(db, 99999, "A", 1)
