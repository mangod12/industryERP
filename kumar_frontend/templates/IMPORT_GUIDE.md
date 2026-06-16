# CSV Import Guide

These files are templates for future uploads:

- `production_tracking_tcil_template.csv`
- `assembly_list_template.csv`
- `assembly_part_list_template.csv`
- `stage_update_template.csv`
- `scrap_import_template.csv`

## Production Tracking Upload

Use from `Customers` -> select customer -> `Upload`.

Accepted workbook types: `.csv`, `.xlsx`, `.xlsm`, `.xltx`, `.xltm`.

Important headers:

- `Drawing no` or `Item Code`: drawing/item identifier.
- `NAME`, `ASSEMBLY`, or `Item Name`: item name.
- `PROFILE` or `Section`: raw material/profile. This must match Raw Materials for automatic material matching.
- `QTY.` or `Qty`: quantity. Defaults to `1` if blank.
- `WT-(kg)`, `UNIT WT.`, `UNITWT.`, or `Weight`: weight per unit.
- `Length (mm)` or `LENGTH`: optional length.
- `Remarks`: optional notes.

## Stage Update Upload

Endpoint: `POST /excel/upload-stage/{stage}`

Valid stages:

- `fabrication`
- `painting`
- `dispatch`

Important headers:

- `Item Code` or `Drawing no`: item identifier.
- `NAME`: fallback item name.
- `Status`: `completed`, `done`, `yes`, `1`, `true`, `complete`, `in_progress`, `wip`, `working`, or `started`.
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
