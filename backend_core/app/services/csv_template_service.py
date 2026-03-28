"""
CSV Template Service — Generate downloadable sample CSV templates.

Every import area gets a sample template with headers + realistic example rows
matching the steel fabrication domain.
"""
import csv
import io
from fastapi.responses import StreamingResponse


def _make_csv_response(headers: list, rows: list, filename: str) -> StreamingResponse:
    """Build a StreamingResponse with CSV content."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def bom_combined_template() -> StreamingResponse:
    """Combined assembly + parts CSV template."""
    headers = [
        "assembly_code", "assembly_name", "drawing_number", "lot_number",
        "mark_number", "part_name", "section", "length_mm", "width_mm",
        "thickness_mm", "qty", "weight_per_unit_kg", "material_grade",
    ]
    rows = [
        ["HR110", "Handrail Type A", "TCI-SFD-49-02-03-07-300-03544", "LOT-03",
         "HR110-01", "Top Rail", "40 NB(M) PIPE", "868", "", "", "1", "3.09", "IS 2062 E250"],
        ["HR110", "Handrail Type A", "TCI-SFD-49-02-03-07-300-03544", "LOT-03",
         "HR110-02", "Vertical Post", "40 NB(M) PIPE", "157", "", "", "2", "0.56", "IS 2062 E250"],
        ["HR110", "Handrail Type A", "TCI-SFD-49-02-03-07-300-03544", "LOT-03",
         "HR110-03", "Base Plate", "PL08", "60", "60", "8", "2", "0.23", "IS 2062 E250"],
    ]
    return _make_csv_response(headers, rows, "bom_combined_template.csv")


def bom_assemblies_template() -> StreamingResponse:
    """Assembly-level CSV template."""
    headers = [
        "assembly_code", "assembly_name", "drawing_number", "lot_number",
        "ordered_qty", "notes",
    ]
    rows = [
        ["HR110", "Handrail Type A", "TCI-SFD-49-02-03-07-300-03544", "LOT-03", "1", "TCIL CAL Furnace Bay"],
        ["HR111", "Handrail Type B", "TCI-SFD-49-02-03-07-300-03545", "LOT-03", "1", "TCIL CAL Furnace Bay"],
        ["HR116", "Handrail Standard", "TCI-SFD-49-02-03-07-300-03550", "LOT-02", "24", "TCIL CAL Furnace Bay"],
    ]
    return _make_csv_response(headers, rows, "assemblies_template.csv")


def bom_parts_template() -> StreamingResponse:
    """Parts-level CSV template."""
    headers = [
        "assembly_code", "mark_number", "part_name", "section",
        "length_mm", "width_mm", "thickness_mm", "total_qty",
        "weight_per_unit_kg", "material_grade",
    ]
    rows = [
        ["HR110", "HR110-01", "Top Rail", "40 NB(M) PIPE", "868", "", "", "1", "3.09", "IS 2062 E250"],
        ["HR110", "HR110-02", "Vertical Post", "40 NB(M) PIPE", "157", "", "", "2", "0.56", "IS 2062 E250"],
        ["HR110", "HR110-03", "Base Plate", "PL08", "60", "60", "8", "2", "0.23", "IS 2062 E250"],
    ]
    return _make_csv_response(headers, rows, "parts_template.csv")


def tracking_template() -> StreamingResponse:
    """Tracking import CSV template."""
    headers = [
        "item_code", "item_name", "section", "length_mm", "quantity",
        "weight_per_unit", "assembly", "lot", "drawing_no",
    ]
    rows = [
        ["HR110-01", "Top Rail", "40 NB(M) PIPE", "868", "1", "3.09", "HR110", "LOT-03", "TCI-SFD-03544"],
        ["HR110-02", "Vertical Post", "40 NB(M) PIPE", "157", "2", "0.56", "HR110", "LOT-03", "TCI-SFD-03544"],
        ["HR116-01", "Handrail Post", "50 NB(M) PIPE", "1050", "24", "4.52", "HR116", "LOT-02", "TCI-SFD-03550"],
    ]
    return _make_csv_response(headers, rows, "tracking_template.csv")


def stage_update_template(stage: str) -> StreamingResponse:
    """Stage update CSV template."""
    headers = ["item_code", "status", "qty_completed", "stage_notes"]
    rows = [
        ["HR110-01", "completed", "1", "Welding done, QC passed"],
        ["HR110-02", "in_progress", "1", "Second piece pending"],
        ["HR116-01", "completed", "24", "All pieces done"],
    ]
    return _make_csv_response(headers, rows, f"{stage}_update_template.csv")


def scrap_template() -> StreamingResponse:
    """Scrap import CSV template."""
    headers = ["material", "dimensions", "weight_kg", "qty", "reason_code"]
    rows = [
        ["40 NB(M) PIPE", "200mm offcut", "1.5", "3", "cutting_waste"],
        ["PL08", "60x60mm", "0.23", "1", "defect"],
        ["50 NB(M) PIPE", "500mm offcut", "3.8", "2", "leftover"],
    ]
    return _make_csv_response(headers, rows, "scrap_template.csv")


def inventory_template() -> StreamingResponse:
    """Inventory import CSV template."""
    headers = ["name", "unit", "total_qty", "used_qty", "category"]
    rows = [
        ["40 NB(M) PIPE", "kg", "5000", "0", "pipe"],
        ["PL08 Plate 8mm", "kg", "3000", "0", "plate"],
        ["50 NB(M) PIPE", "kg", "2000", "0", "pipe"],
    ]
    return _make_csv_response(headers, rows, "inventory_template.csv")
