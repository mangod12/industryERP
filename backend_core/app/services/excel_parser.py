"""
Excel Parser — Column detection and data reading utilities.
Extracted from excel.py for separation of concerns.

Contains:
  - DEFAULT_COLUMN_MAPPINGS with 90+ aliases
  - _find_column_mapping() for auto-detection
  - _read_file_to_dataframe() for multi-format reading
"""
import pandas as pd
from io import BytesIO
from typing import Any, Dict, Optional, Tuple


def to_native(value: Any):
    """Convert pandas/numpy types to native Python types."""
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


# Column aliases — maps common Excel/CSV column names to database fields
DEFAULT_COLUMN_MAPPINGS: Dict[str, list] = {
    "item_code": [
        "item code", "item_code", "code", "mark number", "mark_number",
        "mark no", "mark no.", "marking", "item no", "item no.",
        "item number", "mark", "sl no", "sl. no.", "serial",
        "sr no", "sr. no.", "drawing no", "drawing_no", "drg no",
        "drg. no.", "drawing number", "drawing_number",
    ],
    "item_name": [
        "item name", "item_name", "name", "description", "item description",
        "item_description", "material", "material name", "material_name",
        "part name", "part_name", "component", "component name",
        "member", "member name", "member_name", "element",
        "size", "section size", "profile",
    ],
    "section": [
        "section", "section size", "section_size", "steel section",
        "profile", "profile name", "shape", "type", "material type",
        "grade", "steel grade", "specification", "spec",
    ],
    "length_mm": [
        "length", "length_mm", "length (mm)", "length(mm)",
        "len", "len (mm)", "length mm", "l (mm)", "l(mm)",
    ],
    "quantity": [
        "quantity", "qty", "qty.", "quantity (nos)", "nos",
        "nos.", "no of pieces", "no. of pieces", "pieces",
        "pcs", "pcs.", "numbers", "count", "total qty",
        "total_qty", "ordered qty", "ordered_qty",
    ],
    "weight_per_unit": [
        "weight per unit", "weight_per_unit", "unit weight",
        "unit_weight", "wt per unit", "wt/unit", "weight/unit",
        "weight each", "unit wt", "unit wt.", "wt (kg)",
        "weight (kg)", "weight_kg", "weight", "wt", "wt.",
        "weight per piece", "wt per piece", "wt/pc",
    ],
    "unit": [
        "unit", "uom", "unit of measure", "measure",
    ],
    "assembly": [
        "assembly", "assembly_code", "assembly code", "assy",
        "assy code", "assembly no", "assembly_no",
    ],
    "lot": [
        "lot", "lot_number", "lot number", "lot no", "lot no.",
        "batch", "batch no", "batch_number",
    ],
}


def find_column_mapping(columns: list) -> Dict[str, Optional[str]]:
    """
    Auto-detect column mapping from Excel/CSV headers.
    Returns dict mapping database field names to detected column names.
    """
    mapping = {}
    cols_lower = {c: c.strip().lower() for c in columns}

    for field, aliases in DEFAULT_COLUMN_MAPPINGS.items():
        matched = None
        for col, col_lower in cols_lower.items():
            if col_lower in aliases:
                matched = col
                break
        mapping[field] = matched

    return mapping


def read_file_to_dataframe(
    content: bytes, filename: str
) -> Tuple[pd.DataFrame, str]:
    """
    Read file content into DataFrame. Supports Excel and CSV.
    Returns (DataFrame, detected_format).
    """
    if filename.endswith((".xlsx", ".xls")):
        try:
            xls = pd.ExcelFile(BytesIO(content))
            sheet = xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet)
            return df, "excel"
        except Exception as e:
            raise ValueError(f"Could not parse Excel file: {e}")

    if filename.endswith(".csv"):
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(BytesIO(content), encoding=encoding)
                return df, "csv"
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError("Could not parse CSV file with any supported encoding")

    raise ValueError(f"Unsupported file format: {filename}")
