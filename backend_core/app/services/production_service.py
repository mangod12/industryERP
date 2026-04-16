import pandas as pd
import json
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .. import models
from ..models import Customer, ProductionItem, StageTracking, Inventory, MaterialUsage, Notification, ExcelUpload

class ProductionService:
    # Public constant for column mappings
    DEFAULT_MAPPINGS = {
        "item_code": ["item_code", "item code", "code", "sr no", "sr.no", "s.no", "sno", "id", "part no", "part_no", "drawing no", "drawing_no", "dwg no", "dwg"],
        "item_name": ["item_name", "item name", "name", "description", "item", "material", "part name", "part_name", "product"],
        "section": ["section", "size", "profile", "type", "category", "grade"],
        "length_mm": ["length_mm", "length mm", "length", "length (mm)", "len", "size_mm"],
        "quantity": ["quantity", "qty", "qty.", "count", "nos", "no", "pcs", "pieces"],
        "unit": ["unit", "uom", "units"],
        "weight_per_unit": ["weight_per_unit", "weight", "wt", "wt.", "wt-(kg)", "wt (kg)", "weight (kg)", "weight/unit", "unit weight"],
        "notes": ["notes", "remarks", "comment", "comments"],
    }

    @staticmethod
    def to_native(value: Any):
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

    @staticmethod
    def read_file_to_dataframe(content: bytes, filename: str) -> Dict[str, pd.DataFrame]:
        filename_lower = filename.lower()
        if filename_lower.endswith(".xlsx"):
            return pd.read_excel(BytesIO(content), sheet_name=None, engine="openpyxl")
        elif filename_lower.endswith(".csv"):
            try:
                # Try common encodings
                for enc in ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']:
                    try:
                        # rewind buffer for each attempt
                        content_io = BytesIO(content)
                        return {"Sheet1": pd.read_csv(content_io, encoding=enc)}
                    except UnicodeDecodeError:
                        continue
                # Fallback
                return {"Sheet1": pd.read_csv(BytesIO(content), encoding='utf-8', errors='ignore')}
            except Exception as e:
                raise ValueError(f"Failed to read CSV: {str(e)}")
        raise ValueError("Unsupported file format")

    @classmethod
    def get_column_mapping(cls, columns: List[str]) -> Dict[str, str]:
        mapping = {}
        for col in columns:
            col_lower = col.lower().strip()
            for db_field, file_fields in cls.DEFAULT_MAPPINGS.items():
                if col_lower in file_fields:
                    if db_field not in mapping.values():
                        mapping[col] = db_field
                    break
        return mapping

    @classmethod
    def _aggregate_dataframe(cls, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Aggregates dataframe rows by duplicate Item Code (or Name if code missing).
        Sums Quantity, keeps first occurrence of other fields.
        Fail-safe: Returns original dataframe if aggregation crashes.
        """
        if df.empty:
            return df
            
        try:
            field_to_col = {v: k for k, v in mapping.items()}
            col_code = field_to_col.get("item_code")
            col_name = field_to_col.get("item_name")
            col_qty = field_to_col.get("quantity")
            
            if not col_code:
                return df

            # Create a grouping key (prefer code, fallback to name)
            # We'll use a temporary column for grouping to handle missing codes safely
            # Make a copy to avoid SettingWithCopy warnings on the original df
            df = df.copy()
            
            df['_group_key'] = df[col_code].astype(str).str.strip().str.lower()
            if col_name:
                 # logical fallback: if code is empty/nan, usage name? 
                 mask = df['_group_key'].isna() | (df['_group_key'] == 'nan') | (df['_group_key'] == '')
                 if col_name and mask.any():
                     df.loc[mask, '_group_key'] = df.loc[mask, col_name].astype(str).str.strip().str.lower()
            
            # Define aggregation rules
            agg_rules = {c: 'first' for c in df.columns if c not in [col_qty, '_group_key']}
            if col_qty:
                # Ensure quantity is numeric
                df[col_qty] = pd.to_numeric(df[col_qty], errors='coerce').fillna(0)
                agg_rules[col_qty] = 'sum'
                
            # Perform aggregation
            df_agg = df.groupby('_group_key', as_index=False).agg(agg_rules)
            
            # Re-map columns back to a clean state if needed, but here we already have clean columns
            return df_agg
            
        except Exception as e:
            print(f"[Aggregation Error] Failed to aggregate rows: {e}")
            return df

    @staticmethod
    def _find_inventory_match(profile: str, db: Session, item_code: str = None) -> Optional[Inventory]:
        # 0. Check Manual Mappings First
        if profile:
            mapping = db.query(models.MaterialMapping).filter(
                models.MaterialMapping.excel_name.ilike(profile.strip())
            ).first()
            if mapping:
                return db.query(models.Inventory).get(mapping.material_id)
        
        # Helper inner function for core matching logic
        def try_match(search_str: str):
            if not search_str or str(search_str).lower() == 'nan':
                return None
            clean = str(search_str).strip().upper()
            
            # 1. Direct Match
            match = db.query(Inventory).filter(
                or_(
                    Inventory.name.ilike(clean),
                    Inventory.section.ilike(clean),
                    Inventory.code.ilike(clean)
                )
            ).first()
            if match: return match
            
            # 2. Fuzzy Match
            normalized = clean.replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
            
            all_inv = db.query(Inventory).all() 
            for inv in all_inv:
                inv_norm = (inv.name or '').upper().replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
                if normalized == inv_norm or normalized in inv_norm or inv_norm in normalized:
                    return inv
                if inv.section:
                    sec_norm = inv.section.upper().replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
                    if normalized == sec_norm or normalized in sec_norm or sec_norm in normalized:
                        return inv
                if inv.code:
                    code_norm = inv.code.upper().replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
                    if normalized == code_norm:
                        return inv
            return None

        # Try matching by Profile / Section first
        match = try_match(profile)
        if match: return match
        
        # Fallback: Try matching by Item Code
        if item_code:
            match = try_match(item_code)
            if match: return match
            
        return None
        # Optimize: Fetch all potentially relevant items first might be better if inventory is huge, 
        # but for now iterating is safer for logic migration correctness
        all_inv = db.query(Inventory).all() 
        for inv in all_inv:
            inv_norm = (inv.name or '').upper().replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
            if normalized in inv_norm or inv_norm in normalized:
                return inv
            if inv.section:
                sec_norm = inv.section.upper().replace('X', '*').replace('x', '*').replace(' ', '').replace('-', '')
                if normalized in sec_norm or sec_norm in normalized:
                    return inv
        return None

    @classmethod
    def preview_production_excel(cls, db: Session, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Preview Excel content and check inventory matches without committing changes.
        """
        dfs = cls.read_file_to_dataframe(file_content, filename)
        df_raw = list(dfs.values())[0] # Use first sheet
        
        cols = [str(c).strip() for c in df_raw.columns]
        mapping = cls.get_column_mapping(cols)
        
        # Aggregate Duplicates Logic
        df = cls._aggregate_dataframe(df_raw, mapping)
        
        field_to_col = {v: k for k, v in mapping.items()}
        
        preview_rows = []
        matched_profiles = []
        unmatched_profiles = []
        seen_profiles = set()
        
        total_weight_matched = 0.0
        total_weight_unmatched = 0.0
        total_rows = len(df)  # Get total row count
        
        for idx, row in df.iterrows():
            row_data = {col: cls.to_native(row.get(col)) for col in cols}
            
            # Logic check
            section = cls.to_native(row.get(field_to_col.get("section")))
            code_val = cls.to_native(row.get(field_to_col.get("item_code")))
            weight = cls.to_native(row.get(field_to_col.get("weight_per_unit")))
            qty = cls.to_native(row.get(field_to_col.get("quantity"), 1))
            
            try:
                weight_val = float(weight) if weight is not None else 0.0
            except (ValueError, TypeError):
                weight_val = 0.0
                
            try:
                qty_val = float(qty) if qty is not None else 1.0
            except (ValueError, TypeError):
                qty_val = 1.0
            
            item_total = float(weight_val * qty_val)
            
            match_status = "⚠️ Not Found"
            inv_name = "-"
            
            if section or code_val:
                inv = cls._find_inventory_match(str(section) if section else None, db, item_code=str(code_val) if code_val else None)
                if inv:
                    match_status = "✅ Matched"
                    inv_name = inv.name
                    if str(section) not in seen_profiles:
                        matched_profiles.append(str(section))
                        seen_profiles.add(str(section))
                    total_weight_matched += item_total
                else:
                    if str(section) not in seen_profiles:
                        unmatched_profiles.append(str(section))
                        seen_profiles.add(str(section))
                    total_weight_unmatched += item_total
            
            row_data["__material_status"] = match_status
            row_data["__inventory_name"] = inv_name
            row_data["__total_weight"] = item_total
            
            if len(preview_rows) < 20:
                preview_rows.append(row_data)
            
        return {
            "columns": cols,
            "total_rows": total_rows,  # Include total row count
            "preview_rows": preview_rows,
            "material_matching": {
                "matched_profiles": matched_profiles,
                "unmatched_profiles": unmatched_profiles,
                "total_weight_matched_kg": total_weight_matched,
                "total_weight_unmatched_kg": total_weight_unmatched,
                "grand_total_weight_kg": total_weight_matched + total_weight_unmatched,
                "note": "Preview limited to first 20 rows."
            }
        }

    @classmethod
    def process_production_excel(cls, db: Session, file_content: bytes, filename: str, user_id: int, customer_id: Optional[int] = None, deduct_from_inventory_id: Optional[int] = None):
        """
        Transactional processing of production Excel file.
        1. Reads file
        2. Gets/Creates Customer (if not provided) -> Actually for now we expect customer_id usually, 
           but if we want to extract from file we could. Sticking to `customer_id` passed in for now as per router.
        3. Creates Upload Record
        4. Processes Items -> Creates ProductionItems, StageTracking, and Deducts Inventory
        """
        
        # 1. Read
        dfs = cls.read_file_to_dataframe(file_content, filename)
        # Use first sheet by default
        df_raw = list(dfs.values())[0]
        
        # Normalize columns: lower and strip
        df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]
        mapping = cls.get_column_mapping(df_raw.columns.tolist())
        
        # field_to_col maps DB field to normalized column name
        field_to_col = {v: k for k, v in mapping.items()}
        
        # Aggregate Duplicates (using normalized columns)
        df = cls._aggregate_dataframe(df_raw, mapping)
        
        # 2. Upload Record
        upload = ExcelUpload(filename=filename, uploaded_by=user_id)
        db.add(upload)
        db.flush() # Get ID
        
        # 3. Process Rows
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "grand_total_weight_kg": 0.0
        }
        
        customer = db.query(Customer).get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Pre-fetch existing items for deduplication
        existing = db.query(ProductionItem).filter(ProductionItem.customer_id == customer_id).all()
        existing_map = {
            (i.item_code or "").lower(): i for i in existing
        }
        # Also map by name if code missing
        existing_name_map = {
            (i.item_name or "").lower(): i for i in existing
        }

        row_idx = 0
        for _, row in df.iterrows():
            row_idx += 1
            try:
                # Extract Data
                code = cls.to_native(row.get(field_to_col.get("item_code")))
                name = cls.to_native(row.get(field_to_col.get("item_name")))
                
                if not name or pd.isna(name):
                    continue # Skip empty rows
                
                code_str = str(code).strip() if code else f"ITEM-{upload.id}-{row_idx}"
                name_str = str(name).strip()
                
                # Check Dedupe strictly by item_code
                item = existing_map.get(code_str.lower())
                
                # Update/Create values
                section = cls.to_native(row.get(field_to_col.get("section")))
                length = cls.to_native(row.get(field_to_col.get("length_mm")))
                qty_val = cls.to_native(row.get(field_to_col.get("quantity"), 1))
                unit = cls.to_native(row.get(field_to_col.get("unit")))
                weight = cls.to_native(row.get(field_to_col.get("weight_per_unit")))
                notes = cls.to_native(row.get(field_to_col.get("notes")))
                
                try: length = int(float(length)) if length else None
                except: length = None
                
                try: qty = float(qty_val) if qty_val else 1.0
                except: qty = 1.0
                
                try: weight = float(weight) if weight else 0.0
                except: weight = 0.0

                # Calculate total weight for this item (for grand total)
                item_weight = weight * qty
                stats["grand_total_weight_kg"] += item_weight
                
                if item:
                    # Update
                    if item.fabrication_deducted:
                        stats["skipped"] += int(qty)
                        continue # Skip updates if already processed downstream
                    
                    item.section = str(section) if section else item.section
                    item.length_mm = length
                    item.quantity = qty
                    item.unit = str(unit) if unit else item.unit
                    item.weight_per_unit = weight
                    item.notes = str(notes) if notes else item.notes
                    
                    stats["updated"] += int(qty)
                else:
                    # Create
                    item = ProductionItem(
                        customer_id=customer_id,
                        item_code=code_str,
                        item_name=name_str,
                        section=str(section) if section else None,
                        length_mm=length,
                        quantity=qty,
                        unit=str(unit) if unit else None,
                        weight_per_unit=weight,
                        notes=str(notes) if notes else None,
                        excel_upload_id=upload.id,
                        current_stage="fabrication"
                    )
                    db.add(item)
                    db.flush() # Get ID
                    
                    # Initialize ALL tracking stages (fabrication, painting, dispatch)
                    for stage_name in ["fabrication", "painting", "dispatch"]:
                        stage = StageTracking(
                            production_item_id=item.id,
                            stage=stage_name,
                            status="pending",
                            updated_by=user_id
                        )
                        db.add(stage)
                    
                    # Update Maps
                    existing_map[code_str.lower()] = item
                    existing_name_map[name_str.lower()] = item
                    stats["created"] += int(qty)

                
            except Exception as e:
                stats["errors"].append(f"Row {row_idx}: {str(e)}")

        # BULK DEDUCTION: Deduct grand total weight from selected inventory
        if deduct_from_inventory_id and stats["grand_total_weight_kg"] > 0:
            inventory_item = db.query(Inventory).filter(Inventory.id == deduct_from_inventory_id).first()
            if inventory_item:
                # Deduct the grand total
                inventory_item.used = (inventory_item.used or 0) + stats["grand_total_weight_kg"]
                db.add(inventory_item)
                
                # Create a single MaterialUsage record for the bulk deduction
                usage = MaterialUsage(
                    customer_id=customer_id,
                    production_item_id=None,  # Bulk deduction, not tied to single item
                    name=inventory_item.name,
                    qty=stats["grand_total_weight_kg"],
                    unit=inventory_item.unit,
                    by=f"Bulk deduction from Excel import (User {user_id}, File: {filename})",
                    applied=True
                )
                db.add(usage)
                
                # Check for low stock
                available = (inventory_item.total or 0) - inventory_item.used
                if available < ((inventory_item.total or 0) * 0.15):
                    notif = Notification(
                        user_id=user_id,
                        role="Boss",
                        message=f"Low Stock Alert: {inventory_item.name} - Used {stats['grand_total_weight_kg']:.2f} kg, Remaining: {available:.2f} kg",
                        level="warning",
                        category="low_inventory"
                    )
                    db.add(notif)
                    
                    
                # Safe print that won't crash on Windows non-utf8 consoles
                try:
                    print(f"[BULK DEDUCTION] Deducted {stats['grand_total_weight_kg']:.2f} kg from {inventory_item.name}")
                except Exception:
                    pass
            else:
                try:
                    print(f"[BULK DEDUCTION] Inventory item {deduct_from_inventory_id} not found")
                except Exception:
                    pass

        db.commit()
        return stats
