from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from typing import List, Any, Optional, Dict, Tuple
import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json

from .deps import get_current_user, get_db, require_role
from . import models
from .services.production_service import ProductionService

router = APIRouter()

@router.post("/upload")
async def upload_excel(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    """Upload and preview Excel/CSV file contents without importing."""
    filename = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    try:
        # Use service to read file
        dfs = ProductionService.read_file_to_dataframe(content, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sheets = []
    for sheet_name, df in dfs.items():
        cols = [str(c).strip() for c in df.columns.tolist()]
        rows = []
        for _, r in df.iterrows():
            rows.append([ProductionService.to_native(v) for v in r.tolist()])
        
        # Auto-detect column mapping
        detected_mapping = ProductionService.get_column_mapping(cols)
        
        sheets.append({
            "sheet_name": sheet_name,
            "columns": cols,
            "rows": rows,
            "detected_mapping": detected_mapping,
            "row_count": len(rows),
        })

    return {"sheets": sheets}


@router.post("/import-tracking/{customer_id}")
async def import_tracking_excel(
    customer_id: int,
    file: UploadFile = File(...),
    inventory_id: Optional[int] = Query(None, description="Inventory item ID to deduct grand total weight from"),
    sheet_name: Optional[str] = Query(None), # Deprecated in service but kept signature
    column_mapping: Optional[str] = Query(None), # Deprecated
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """
    Import Excel file as tracking items using Central Production Service.
    Transactional: Creates items, customer data, and deducts inventory in one go.
    
    If inventory_id is provided, the grand total weight will be deducted from that inventory item.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    try:
        stats = ProductionService.process_production_excel(
            db=db,
            file_content=content,
            filename=file.filename or "upload.xlsx",
            user_id=current_user.id,
            customer_id=customer_id,
            deduct_from_inventory_id=inventory_id
        )
        
        msg_parts = []
        if stats["created"]: msg_parts.append(f"{stats['created']} created")
        if stats["updated"]: msg_parts.append(f"{stats['updated']} updated")
        if stats["skipped"]: msg_parts.append(f"{stats['skipped']} skipped")
        
        # Add deduction info
        deduction_msg = ""
        if stats.get("grand_total_weight_kg", 0) > 0:
            deduction_msg = f", Grand Total: {stats['grand_total_weight_kg']:.2f} kg"
            if inventory_id:
                deduction_msg += " (deducted from inventory)"
        
        return {
            "message": f"Import complete: {', '.join(msg_parts)}{deduction_msg}",
            "stats": stats,
            "grand_total_weight_kg": stats.get("grand_total_weight_kg", 0)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")



@router.post("/preview-import/{customer_id}")
async def preview_import_excel(
    customer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """
    Preview Excel/CSV file BEFORE importing - uses ProductionService.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
    try:
        preview = ProductionService.preview_production_excel(db, content, file.filename or "upload.xlsx")
        
        customer = db.query(models.Customer).get(customer_id)
        
        # Add file_info with total_rows and matched/unmatched counts for frontend compatibility
        material_matching = preview["material_matching"]
        material_matching["matched_count"] = len(material_matching.get("matched_profiles", []))
        material_matching["unmatched_count"] = len(material_matching.get("unmatched_profiles", []))
        
        return {
            "customer": {"id": customer.id, "name": customer.name} if customer else None,
            "file_info": {
                "columns": preview["columns"],
                "total_rows": preview.get("total_rows", len(preview["preview_rows"]))
            },
            "column_mapping": ProductionService.get_column_mapping(preview["columns"]),
            "material_matching": material_matching,
            "preview_rows": preview["preview_rows"],
            "ready_to_import": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/template")
async def get_excel_template(current_user = Depends(get_current_user)):
    """
    Returns information about the expected Excel format.
    """
    return {
        "message": "Excel template information",
        "supported_columns": {
            "item_code": ["Item Code", "Code", "Sr No", "S.No", "Part No", "ID"],
            "item_name": ["Item Name", "Name", "Description", "Material", "Part Name", "Product"],
            "section": ["Section", "Size", "Profile", "Type", "Category", "Grade"],
            "length_mm": ["Length (mm)", "Length", "Len", "Size_mm"],
            "quantity": ["Quantity", "Qty", "Count", "Nos", "Pcs", "Pieces"],
            "unit": ["Unit", "UOM", "Units"],
            "weight_per_unit": ["Weight", "Wt", "Weight/Unit", "Unit Weight"],
            "notes": ["Notes", "Remarks", "Comments"],
        },
        "example_format": {
            "columns": ["Sr No", "Item Name", "Section", "Length (mm)", "Qty", "Unit", "Remarks"],
            "sample_row": ["1", "Steel Beam", "IPE 200", "6000", "10", "Pcs", "Main structure"]
        },
        "notes": [
            "The system automatically detects column names",
            "Not all columns are required - minimum is Item Name",
        ]
    }
async def get_excel_template(current_user = Depends(get_current_user)):
    """
    Returns information about the expected Excel format.
    The system is flexible and can handle various column names.
    """
    return {
        "message": "Excel template information",
        "supported_columns": {
            "item_code": ["Item Code", "Code", "Sr No", "S.No", "Part No", "ID"],
            "item_name": ["Item Name", "Name", "Description", "Material", "Part Name", "Product"],
            "section": ["Section", "Size", "Profile", "Type", "Category", "Grade"],
            "length_mm": ["Length (mm)", "Length", "Len", "Size_mm"],
            "quantity": ["Quantity", "Qty", "Count", "Nos", "Pcs", "Pieces"],
            "unit": ["Unit", "UOM", "Units"],
            "weight_per_unit": ["Weight", "Wt", "Weight/Unit", "Unit Weight"],
            "notes": ["Notes", "Remarks", "Comments"],
        },
        "example_format": {
            "columns": ["Sr No", "Item Name", "Section", "Length (mm)", "Qty", "Unit", "Remarks"],
            "sample_row": ["1", "Steel Beam", "IPE 200", "6000", "10", "Pcs", "Main structure"]
        },
        "notes": [
            "The system automatically detects column names",
            "Column order doesn't matter",
            "Not all columns are required - minimum is Item Name",
            "Multiple sheets are supported - specify sheet_name parameter to select",
            "Both .xlsx and .csv files are supported",
        ]
    }


@router.delete("/{upload_id}")
def delete_excel_upload(upload_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Software Supervisor")), force: bool = False):
    """Controlled delete for Excel uploads. Only Software Supervisor can request delete.
    If any item from the upload is completed, delete is blocked unless `force=True` and current_user is Boss.
    """
    upload = db.query(models.ExcelUpload).filter(models.ExcelUpload.id == upload_id, models.ExcelUpload.is_deleted == False).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    completed_items = db.query(models.ProductionItem).filter(
        models.ProductionItem.excel_upload_id == upload_id,
        models.ProductionItem.is_completed == True
    ).count()

    if completed_items > 0:
        # Only Boss can force-delete
        if not (force and getattr(current_user, 'role', '') == 'Boss'):
            raise HTTPException(status_code=400, detail="Cannot delete Excel upload with completed tracking")

    upload.is_deleted = True
    db.commit()

    return {"message": "Excel upload deleted safely"}


@router.post("/upload-stage/{stage}")
async def upload_stage_excel(
    stage: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """
    Upload Excel/CSV file to update items at a specific stage.
    
    Stage can be: fabrication, painting, dispatch
    
    The file should contain item identifiers (Drawing no, item_code, Assembly, or item_name) to match existing items.
    Additional columns can include stage-specific data like completion status, notes, etc.
    
    Supports columns like: Drawing no, ASSEMBLY, NAME, PROFILE, QTY., WT-(kg), AR(m²), PRIORITY, PAINT, DATE, LOT
    """
    from datetime import datetime
    
    stage = stage.lower()
    valid_stages = ["fabrication", "painting", "dispatch"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .csv files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_data = ProductionService.read_file_to_dataframe(content, filename)

    if not file_data:
        raise HTTPException(status_code=400, detail="File contains no data")

    # Use first sheet
    df = list(file_data.values())[0]
    cols = [str(c).strip() for c in df.columns.tolist()]
    
    # Extended column mappings for stage data
    stage_column_mappings = {
        **ProductionService.DEFAULT_MAPPINGS,
        # Status variations
        "status": "status", "stage_status": "status", "completion": "status",
        "completed": "status", "done": "status", "state": "status",
        # Quantity completed variations
        "qty_completed": "qty_completed", "completed_qty": "qty_completed",
        "done_qty": "qty_completed", "finished": "qty_completed",
        # Stage notes
        "stage_notes": "stage_notes", "stage_remarks": "stage_notes",
        "work_notes": "stage_notes", "completion_notes": "stage_notes",
    }
    
    # Find column mapping
    mapping = {}
    for col in cols:
        col_lower = col.lower().strip()
        if col_lower in stage_column_mappings:
            db_field = stage_column_mappings[col_lower]
            if db_field not in mapping.values():
                mapping[col] = db_field
    
    field_to_col = {v: k for k, v in mapping.items()}
    
    items_updated = 0
    items_not_found = []
    errors = []
    stage_updates: List[Dict[str, Any]] = []
    
    for idx, row in df.iterrows():
        try:
            # Get item identifier
            item_code = ProductionService.to_native(row.get(field_to_col.get('item_code', ''), None))
            item_name = ProductionService.to_native(row.get(field_to_col.get('item_name', ''), None))
            
            # Skip empty rows
            if (not item_code or str(item_code) == 'nan') and (not item_name or str(item_name) == 'nan'):
                continue
            
            # Find matching production item
            query = db.query(models.ProductionItem)
            if item_code and str(item_code) != 'nan':
                query = query.filter(models.ProductionItem.item_code == str(item_code))
            elif item_name and str(item_name) != 'nan':
                query = query.filter(models.ProductionItem.item_name == str(item_name))
            
            item = query.first()
            
            if not item:
                items_not_found.append(f"Row {idx + 1}: {item_code or item_name}")
                continue
            
            # Get or create stage tracking
            stage_tracking = db.query(models.StageTracking).filter(
                models.StageTracking.production_item_id == item.id,
                models.StageTracking.stage == stage
            ).first()
            
            if not stage_tracking:
                stage_tracking = models.StageTracking(
                    production_item_id=item.id,
                    stage=stage,
                    status="pending"
                )
                db.add(stage_tracking)
            
            # Update stage status if provided
            status = ProductionService.to_native(row.get(field_to_col.get('status', ''), None))
            if status and str(status) != 'nan':
                status_str = str(status).lower()
                if status_str in ['completed', 'done', 'yes', '1', 'true', 'complete']:
                    stage_tracking.status = 'completed'
                    stage_tracking.completed_at = datetime.utcnow()
                elif status_str in ['in_progress', 'in progress', 'wip', 'working', 'started']:
                    stage_tracking.status = 'in_progress'
                    if not stage_tracking.started_at:
                        stage_tracking.started_at = datetime.utcnow()
                else:
                    stage_tracking.status = 'pending'
            
            stage_tracking.updated_by = current_user.id
            
            # Update item notes if provided
            stage_notes = ProductionService.to_native(row.get(field_to_col.get('stage_notes', ''), None))
            if stage_notes and str(stage_notes) != 'nan':
                existing_notes = item.notes or ''
                item.notes = f"{existing_notes}\n[{stage.capitalize()}]: {stage_notes}".strip()
            
            # Update quantity if provided
            quantity = ProductionService.to_native(row.get(field_to_col.get('quantity', ''), None))
            if quantity and str(quantity) != 'nan':
                try:
                    item.quantity = float(quantity)
                except:
                    pass
            
            # Update current_stage if this stage is being marked as completed and it's the current stage
            if hasattr(item, 'current_stage') and stage_tracking.status == 'completed':
                next_stage_map = {"fabrication": "painting", "painting": "dispatch", "dispatch": None}
                next_stage = next_stage_map.get(stage)
                if next_stage and item.current_stage == stage:
                    item.current_stage = next_stage
                    item.stage_updated_at = datetime.utcnow()
                    item.stage_updated_by = current_user.id
            
            db.add(stage_tracking)
            db.add(item)
            items_updated += 1
            
            stage_updates.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "stage": stage,
                "status": stage_tracking.status,
            })
            
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"Stage '{stage}' Excel processed: {items_updated} items updated",
        "stage": stage,
        "items_updated": items_updated,
        "items_not_found": items_not_found if items_not_found else None,
        "column_mapping_used": mapping,
        "updates": stage_updates[:20],  # First 20 updates as preview
        "errors": errors if errors else None,
    }


@router.post("/preview-stage/{stage}")
async def preview_stage_excel(
    stage: str,
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """
    Preview Excel/CSV file for stage upload without actually importing.
    Shows matched items and detected columns.
    
    Supports both .xlsx and .csv files.
    """
    stage = stage.lower()
    valid_stages = ["fabrication", "painting", "dispatch"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .csv files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_data = ProductionService.read_file_to_dataframe(content, filename)

    if not file_data:
        raise HTTPException(status_code=400, detail="File contains no data")

    # Use first sheet
    df = list(file_data.values())[0]
    cols = [str(c).strip() for c in df.columns.tolist()]
    
    # Find column mapping
    mapping = ProductionService.get_column_mapping(cols)
    
    # Convert rows to list for preview
    rows = []
    for _, r in df.head(10).iterrows():
        row_vals = {}
        for col in cols:
            row_vals[col] = ProductionService.to_native(r.get(col))
        rows.append(row_vals)
    
    return {
        "stage": stage,
        "sheet_name": list(file_data.keys())[0],
        "columns": cols,
        "detected_mapping": mapping,
        "row_count": len(df),
        "preview_rows": rows,
        "instructions": f"This will update items at the '{stage.capitalize()}' stage. Items are matched by Drawing No, Item Code, Assembly, or Item Name.",
    }
