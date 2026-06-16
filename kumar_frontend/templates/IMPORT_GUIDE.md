# CSV Import Guide

These files are upload-ready templates for future data imports:

- `production_tracking_tcil_template.csv`
- `assembly_list_template.csv`
- `assembly_part_list_template.csv`
- `stage_update_template.csv`
- `scrap_import_template.csv`

## Production Tracking Upload

Use from `Customers` -> select customer -> `Upload`.

Accepted workbook types: `.csv`, `.xlsx`, `.xlsm`, `.xltx`, `.xltm`.

Use these preferred headers in new CSV files:

- `Item Code`: drawing/item identifier. Existing aliases include `Drawing no`, `DRGNO`, `Part No`, and `Code`.
- `Item Name`: item name. Existing aliases include `NAME`, `ASSEMBLY`, `Description`, `Part Name`, and `Item`.
- `Section`: raw material/profile. Existing aliases include `PROFILE`, `Size`, `Type`, and `Grade`.
- `Length (mm)`: optional item length. Existing aliases include `LENGTH`, `Length mm`, and `Len`.
- `Qty`: quantity. Defaults to `1` if blank. Existing aliases include `QTY.`, `NO.`, `PCS`, and `Pieces`.
- `Unit`: optional unit of measure.
- `Weight`: weight per unit in kg. Existing aliases include `WT-(kg)`, `UNIT WT.`, `UNITWT.`, `Total Weight`, and `WT`.
- `Remarks`: optional notes.

The import stores total item weight as `Qty * Weight`. Put unit weight in `Weight`; keep any gross/total weight columns only as reference columns.

## Stage Update Upload

Endpoint: `POST /excel/upload-stage/{stage}`

Valid stages:

- `fabrication`
- `painting`
- `dispatch`

Use these headers:

- `Item Code`: matches an existing production item.
- `Item Name`: fallback match if item code is blank.
- `Status`: use `completed`, `done`, `yes`, `1`, `true`, `complete`, `in_progress`, `wip`, `working`, `started`, or `pending`.
- `stage_notes`: notes to append. Use the underscore.
- `Quantity`: optional quantity update.

## Scrap Upload

Use from the Scrap page or endpoint `POST /scrap/upload-csv`.

Required headers:

- `material_name`
- `weight_kg`

Optional headers:

- `reason_code`: `cutting_waste`, `defect`, `damage`, `overrun`, or `leftover`.
- `dimensions`
- `length_mm`
- `width_mm`
- `quantity`
