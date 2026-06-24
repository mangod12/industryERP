from io import BytesIO

from backend_core.app.models import ScrapRecord


def test_excel_templates_endpoint_lists_downloadable_templates(boss_client):
    response = boss_client.get("/excel/templates")

    assert response.status_code == 200
    templates = response.json()["templates"]
    ids = {template["id"] for template in templates}
    assert {"production_tracking", "stage_update", "scrap_import"}.issubset(ids)

    production = next(template for template in templates if template["id"] == "production_tracking")
    assert production["template_url"].endswith("production_tracking_tcil_template.csv")
    assert "Item Name" in production["required_columns"]
    assert ".xlsx" in production["accepted_formats"]

    scrap = next(template for template in templates if template["id"] == "scrap_import")
    assert scrap["template_url"].endswith("scrap_import_template.csv")
    assert scrap["required_columns"] == ["material_name", "weight_kg"]


def test_scrap_preview_upload_does_not_create_records(boss_client, db):
    csv_bytes = (
        b"material_name,weight_kg,reason_code,dimensions,quantity\n"
        b"MS Plate 10mm,112.5,cutting_waste,900mm x 160mm x 10mm,11\n"
        b"ISMB 200 Beam Offcut,78.4,leftover,1850mm ISMB 200 offcut,3\n"
    )

    response = boss_client.post(
        "/scrap/preview-upload",
        files={"file": ("scrap_import_template.csv", BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready_to_import"] is True
    assert payload["records_count"] == 2
    assert payload["total_weight_kg"] == 190.9
    assert payload["grouped_items"][0]["material_name"] == "MS Plate 10mm"
    assert db.query(ScrapRecord).count() == 0


def test_scrap_preview_reports_missing_columns_without_mutation(boss_client, db):
    csv_bytes = b"material_name,reason_code\nMS Plate 10mm,cutting_waste\n"

    response = boss_client.post(
        "/scrap/preview-upload",
        files={"file": ("bad_scrap.csv", BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready_to_import"] is False
    assert payload["missing_columns"] == ["weight_kg"]
    assert db.query(ScrapRecord).count() == 0
