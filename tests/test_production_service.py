"""
Unit tests for ProductionService — column mapping, fuzzy matching,
file reading, and preview imports.
"""

from io import BytesIO

import pandas as pd
import pytest

from backend_core.app.models import MaterialMapping
from backend_core.app.services.production_service import ProductionService
from tests.conftest import (
    create_test_inventory,
)


def _excel_bytes(df: pd.DataFrame, *, header: bool = True, sheet_name: str = "Sheet1") -> bytes:
    stream = BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=header, sheet_name=sheet_name)
    return stream.getvalue()


# ===========================================================================
# TestColumnMapping
# ===========================================================================


class TestColumnMapping:
    """Tests for ProductionService.get_column_mapping() and DEFAULT_MAPPINGS."""

    def test_exact_alias_item_code(self):
        mapping = ProductionService.get_column_mapping(["Item Code", "Description"])
        assert mapping.get("Item Code") == "item_code" or mapping.get("item code") == "item_code"

    def test_known_aliases_resolve_correctly(self):
        columns = ["Sr No", "Description", "Size", "Length", "Qty", "UOM", "Wt (Kg)", "Remarks"]
        mapping = ProductionService.get_column_mapping(columns)

        values = set(mapping.values())
        # sr no -> item_code
        assert "item_code" in values
        # description -> item_name
        assert "item_name" in values
        # size -> section
        assert "section" in values
        # qty -> quantity
        assert "quantity" in values

    def test_case_insensitive_matching(self):
        columns = ["ITEM CODE", "ITEM NAME", "SECTION", "LENGTH", "QUANTITY"]
        mapping = ProductionService.get_column_mapping(columns)
        values = set(mapping.values())
        assert "item_code" in values
        assert "item_name" in values
        assert "section" in values
        assert "quantity" in values

    def test_drawing_no_maps_to_item_code(self):
        mapping = ProductionService.get_column_mapping(["Drawing No", "Part Name"])
        assert mapping.get("Drawing No") == "item_code"

    def test_weight_aliases(self):
        for alias in ["Weight", "Wt", "Wt.", "Wt-(Kg)", "Wt (Kg)", "Weight (Kg)", "Unit Weight"]:
            mapping = ProductionService.get_column_mapping([alias])
            assert mapping.get(alias) == "weight_per_unit", f"'{alias}' should map to weight_per_unit"

    def test_quantity_aliases(self):
        for alias in ["Quantity", "Qty", "Qty.", "Count", "Nos", "Pcs", "Pieces"]:
            mapping = ProductionService.get_column_mapping([alias])
            assert mapping.get(alias) == "quantity", f"'{alias}' should map to quantity"

    def test_unmapped_columns_not_in_result(self):
        mapping = ProductionService.get_column_mapping(["Random Column", "Another One"])
        assert len(mapping) == 0

    def test_no_duplicate_field_assignments(self):
        """If two columns could map to the same field, only the first should win."""
        columns = ["Item Code", "Code"]  # Both could be item_code
        mapping = ProductionService.get_column_mapping(columns)
        field_values = list(mapping.values())
        assert field_values.count("item_code") == 1

    def test_notes_aliases(self):
        for alias in ["Notes", "Remarks", "Comments"]:
            mapping = ProductionService.get_column_mapping([alias])
            assert mapping.get(alias) == "notes", f"'{alias}' should map to notes"

    def test_real_world_aliases_from_uploaded_workbooks(self):
        columns = ["Detail Drg. No.", "Mark Number", "Qty.", "Unit Weight (MT)"]
        mapping = ProductionService.get_column_mapping(columns)

        assert mapping["Detail Drg. No."] == "item_code"
        assert mapping["Mark Number"] == "item_name"
        assert mapping["Qty."] == "quantity"
        assert mapping["Unit Weight (MT)"] == "weight_per_unit"
        assert ProductionService.get_column_mapping(["   ASSEMBLY     "])["   ASSEMBLY     "] == "item_name"

    def test_prefers_real_identifier_alias_over_serial_number(self):
        mapping = ProductionService.get_column_mapping(["SR. NO.", "unique load", "Detail Drg. No."])

        assert "SR. NO." not in mapping
        assert mapping["unique load"] == "item_code"

    def test_prefers_specific_weight_alias_over_generic_wt(self):
        mapping = ProductionService.get_column_mapping(["WT", "P.C WEIGHT", "unit wt"])

        assert mapping["unit wt"] == "weight_per_unit"
        assert "WT" not in mapping
        assert "P.C WEIGHT" not in mapping


# ===========================================================================
# TestFileReading
# ===========================================================================


class TestFileReading:
    """Tests for ProductionService.read_file_to_dataframe()"""

    def test_csv_file_detected_and_read(self):
        csv_content = b"Item Code,Name,Qty\nA001,Beam,10\nA002,Plate,5"
        result = ProductionService.read_file_to_dataframe(csv_content, "test.csv")

        assert "Sheet1" in result
        df = result["Sheet1"]
        assert len(df) == 2
        assert "Item Code" in df.columns

    def test_csv_with_different_encodings(self):
        # Latin-1 encoded content
        csv_content = "Item Code,Name\nA001,Caf\xe9 Steel".encode("latin-1")
        result = ProductionService.read_file_to_dataframe(csv_content, "test.csv")
        assert len(result["Sheet1"]) == 1

    def test_unsupported_file_format_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            ProductionService.read_file_to_dataframe(b"data", "test.txt")

    def test_unsupported_format_doc(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            ProductionService.read_file_to_dataframe(b"data", "test.doc")

    def test_xlsx_detection(self):
        """Verify .xlsx is attempted (will fail with invalid content, but tests detection)."""
        with pytest.raises(Exception):
            # Invalid xlsx content should raise, but the point is it tries openpyxl
            ProductionService.read_file_to_dataframe(b"not-a-real-xlsx", "test.xlsx")

    def test_xltm_file_detected_and_header_row_promoted(self):
        workbook = pd.DataFrame(
            [
                ["SR. NO.", "Building Name", "Detail Drg. No.", "Mark Number", "Qty.", "Unit Weight (MT)"],
                [1, "B1", "DRG-100", "HR-001", 2, 0.10122],
            ]
        )
        result = ProductionService.read_file_to_dataframe(
            _excel_bytes(workbook, header=False),
            "tracking sheet handrail.xltm",
        )

        df = result["Sheet1"]
        assert list(df.columns) == [
            "SR. NO.",
            "Building Name",
            "Detail Drg. No.",
            "Mark Number",
            "Qty.",
            "Unit Weight (MT)",
        ]
        assert len(df) == 1
        assert df.iloc[0]["Detail Drg. No."] == "DRG-100"

    def test_later_excel_header_row_is_detected(self):
        workbook = pd.DataFrame(
            [
                ["", "", "", "", ""],
                ["READY", "lot No.", "DRGNO.", "ITEMNO.", "QUANTITY"],
                ["Y", "LOT-2", "D-200", "ITEM-9", 4],
            ]
        )
        result = ProductionService.read_file_to_dataframe(_excel_bytes(workbook, header=False), "bom.xltm")

        df = result["Sheet1"]
        assert list(df.columns) == ["READY", "lot No.", "DRGNO.", "ITEMNO.", "QUANTITY"]
        assert len(df) == 1
        assert df.iloc[0]["DRGNO."] == "D-200"


# ===========================================================================
# TestInventoryMatching
# ===========================================================================


class TestInventoryMatching:
    """Tests for ProductionService._find_inventory_match() fuzzy matching."""

    def test_direct_section_match(self, db):
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200")
        match = ProductionService._find_inventory_match("ISMC 200", db)
        assert match is not None
        assert match.id == inv.id

    def test_direct_name_match(self, db):
        inv = create_test_inventory(db, name="HR Plate 10mm", section=None)
        match = ProductionService._find_inventory_match("HR Plate 10mm", db)
        assert match is not None
        assert match.id == inv.id

    def test_direct_code_match(self, db):
        inv = create_test_inventory(db, name="Something", code="ISMC-200")
        match = ProductionService._find_inventory_match("ISMC-200", db)
        assert match is not None
        assert match.id == inv.id

    def test_fuzzy_match_x_vs_star(self, db):
        """ISMC200X100 should match ISMC200*100 via normalization."""
        inv = create_test_inventory(db, name="ISMC200*100", section="ISMC200*100")
        match = ProductionService._find_inventory_match("ISMC200X100", db)
        assert match is not None
        assert match.id == inv.id

    def test_fuzzy_match_ignores_spaces_and_dashes(self, db):
        inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200")
        match = ProductionService._find_inventory_match("ISMC-200", db)
        assert match is not None
        assert match.id == inv.id

    def test_fallback_to_item_code_match(self, db):
        inv = create_test_inventory(db, name="Steel Angle", code="ANG-50")
        match = ProductionService._find_inventory_match(None, db, item_code="ANG-50")
        assert match is not None
        assert match.id == inv.id

    def test_no_match_returns_none(self, db):
        match = ProductionService._find_inventory_match("NONEXISTENT", db)
        assert match is None

    def test_manual_mapping_takes_priority(self, db):
        """MaterialMapping should override fuzzy matching."""
        _inv_wrong = create_test_inventory(db, name="ISMC 200 Wrong", section="ISMC 200")
        inv_correct = create_test_inventory(db, name="ISMC 200 Correct")

        # Create manual mapping
        mapping = MaterialMapping(excel_name="ISMC 200", material_id=inv_correct.id)
        db.add(mapping)
        db.commit()

        match = ProductionService._find_inventory_match("ISMC 200", db)
        assert match is not None
        assert match.id == inv_correct.id

    def test_none_profile_none_code_returns_none(self, db):
        match = ProductionService._find_inventory_match(None, db, item_code=None)
        assert match is None

    def test_nan_string_treated_as_no_match(self, db):
        match = ProductionService._find_inventory_match("nan", db)
        assert match is None


# ===========================================================================
# TestPreviewImport
# ===========================================================================


class TestPreviewImport:
    """Tests for ProductionService.preview_production_excel()"""

    def test_preview_returns_correct_structure(self, db):
        csv_content = b"Item Code,Item Name,Section,Quantity,Weight\nA001,Beam,ISMC 200,5,100"

        result = ProductionService.preview_production_excel(db, csv_content, "test.csv")

        assert "columns" in result
        assert "total_rows" in result
        assert "preview_rows" in result
        assert "material_matching" in result
        assert result["total_rows"] == 1

    def test_preview_limits_to_20_rows(self, db):
        # Create CSV with 30 rows
        lines = ["Item Code,Item Name,Section,Quantity,Weight"]
        for i in range(30):
            lines.append(f"A{i:03d},Beam {i},ISMC,1,10")
        csv_content = "\n".join(lines).encode("utf-8")

        result = ProductionService.preview_production_excel(db, csv_content, "big.csv")

        assert result["total_rows"] == 30
        assert len(result["preview_rows"]) == 20

    def test_preview_reports_matched_profiles(self, db):
        _inv = create_test_inventory(db, name="ISMC 200", section="ISMC 200")
        csv_content = b"Item Code,Item Name,Section,Quantity,Weight\nA001,Beam,ISMC 200,5,100"

        result = ProductionService.preview_production_excel(db, csv_content, "test.csv")

        assert "ISMC 200" in result["material_matching"]["matched_profiles"]

    def test_preview_reports_unmatched_profiles(self, db):
        csv_content = b"Item Code,Item Name,Section,Quantity,Weight\nA001,Beam,UNKNOWN STEEL,5,100"

        result = ProductionService.preview_production_excel(db, csv_content, "test.csv")

        assert "UNKNOWN STEEL" in result["material_matching"]["unmatched_profiles"]

    def test_preview_calculates_total_weight(self, db):
        csv_content = b"Item Code,Item Name,Section,Quantity,Weight\nA001,Beam,X,2,50\nA002,Plate,Y,3,100"

        result = ProductionService.preview_production_excel(db, csv_content, "test.csv")

        # 2*50 + 3*100 = 400
        assert result["material_matching"]["grand_total_weight_kg"] == 400.0

    def test_preview_converts_metric_ton_weight_columns_to_kg(self, db):
        csv_content = b"Item Code,Item Name,Quantity,Unit Weight (MT)\nA001,Beam,2,0.5"

        result = ProductionService.preview_production_excel(db, csv_content, "test.csv")

        assert result["material_matching"]["grand_total_weight_kg"] == 1000.0

    def test_preview_handles_padded_excel_headers(self, db):
        content = _excel_bytes(
            pd.DataFrame(
                [
                    {
                        "Drawing no": "P-001",
                        "   ASSEMBLY     ": "ASM-001",
                        "  NAME              ": "HANDRAIL",
                        "   PROFILE           ": "UB203X133X25",
                        "  QTY.         ": 2,
                        "  WT-(kg)       ": 199.139,
                    }
                ]
            ),
            sheet_name="07_TATA_Tracking_Report",
        )

        result = ProductionService.preview_production_excel(db, content, "7. TRACKING REPORT TCIL.xlsx")

        assert result["columns"] == [
            "Drawing no",
            "ASSEMBLY",
            "NAME",
            "PROFILE",
            "QTY.",
            "WT-(kg)",
        ]
        assert result["total_rows"] == 1
        assert len(result["preview_rows"]) == 1
        assert result["preview_rows"][0]["Drawing no"] == "P-001"
        assert result["material_matching"]["grand_total_weight_kg"] == pytest.approx(398.278)


# ===========================================================================
# TestToNative
# ===========================================================================


class TestToNative:
    """Tests for ProductionService.to_native() helper."""

    def test_none_passthrough(self):
        assert ProductionService.to_native(None) is None

    def test_string_passthrough(self):
        assert ProductionService.to_native("hello") == "hello"

    def test_int_passthrough(self):
        assert ProductionService.to_native(42) == 42

    def test_float_passthrough(self):
        assert ProductionService.to_native(3.14) == 3.14

    def test_nan_returns_none(self):
        assert ProductionService.to_native(float("nan")) is None

    def test_numpy_int_converts(self):
        try:
            import numpy as np

            val = np.int64(42)
            result = ProductionService.to_native(val)
            assert result == 42
            assert isinstance(result, int)
        except ImportError:
            pytest.skip("numpy not available")


# ===========================================================================
# TestAggregation
# ===========================================================================


class TestAggregation:
    """Tests for ProductionService._aggregate_dataframe()"""

    def test_aggregation_sums_quantity_for_duplicate_codes(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "Item Code": ["A001", "A001", "A002"],
                "Name": ["Beam", "Beam", "Plate"],
                "Qty": [5, 3, 10],
            }
        )
        mapping = {"Item Code": "item_code", "Name": "item_name", "Qty": "quantity"}

        result = ProductionService._aggregate_dataframe(df, mapping)

        # A001 should be aggregated: 5 + 3 = 8
        assert len(result) == 2
        a001_row = result[result["Item Code"] == "A001"]
        assert a001_row["Qty"].values[0] == 8

    def test_aggregation_returns_original_on_empty_df(self):
        import pandas as pd

        df = pd.DataFrame()
        mapping = {}
        result = ProductionService._aggregate_dataframe(df, mapping)
        assert result.empty

    def test_aggregation_without_item_code_returns_original(self):
        import pandas as pd

        df = pd.DataFrame({"Name": ["A", "B"], "Qty": [1, 2]})
        mapping = {"Name": "item_name", "Qty": "quantity"}
        result = ProductionService._aggregate_dataframe(df, mapping)
        assert len(result) == 2  # No grouping since no item_code in mapping
