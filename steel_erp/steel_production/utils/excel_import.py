"""Excel Import Utility for Steel Production Tracking"""

import frappe
import pandas as pd
from frappe.utils import flt, cstr
import re


# Flexible column mappings - support multiple variations
COLUMN_MAPPINGS = {
	"drawing_number": ["drawing no", "dwg no", "drawing_no", "dwg_no", "drawing", "item code", "item_code"],
	"assembly": ["assembly", "assembly mark", "asm", "mark"],
	"item_name": ["name", "item name", "item_name", "description", "desc"],
	"profile": ["profile", "section", "profile/section", "profile_section", "material"],
	"quantity": ["qty.", "qty", "quantity", "no.", "nos", "no_of_items"],
	"weight": ["wt-(kg)", "wt (kg)", "weight", "wt", "weight_kg", "unit_weight"],
	"area": ["ar(m²)", "ar (m²)", "area", "ar", "area_m2"],
	"paint": ["paint", "paint_spec", "painting"],
	"lot": ["lot 1", "lot_1", "lot1", "lot", "batch", "lot number"],
	"priority": ["priority", "area", "location"],
	"revision": ["rev", "revision", "rev.", "rev_no"],
	"material_grade": ["grade", "material grade", "mat_grade", "steel_grade"]
}


def normalize_column_name(col_name):
	"""Normalize column name for matching"""
	return cstr(col_name).lower().strip()


def find_column(df, possible_names):
	"""Find column in dataframe by matching possible names"""
	normalized_cols = {normalize_column_name(col): col for col in df.columns}
	
	for possible_name in possible_names:
		normalized = normalize_column_name(possible_name)
		if normalized in normalized_cols:
			return normalized_cols[normalized]
	
	return None


@frappe.whitelist()
def import_tracking_excel(file_path, customer, lot_number=None):
	"""
	Import tracking data from Excel/CSV file
	
	Args:
		file_path: Path to Excel or CSV file
		customer: Customer name for production orders
		lot_number: Optional lot number to assign
	
	Returns:
		dict: Import summary with success count, errors, and matched items
	"""
	try:
		# Read file
		if file_path.endswith('.csv'):
			df = pd.read_csv(file_path)
		else:
			df = pd.read_excel(file_path)
		
		# Map columns
		column_map = {}
		for field, possible_names in COLUMN_MAPPINGS.items():
			found_col = find_column(df, possible_names)
			if found_col:
				column_map[field] = found_col
		
		# Validate required columns
		required = ["profile", "quantity"]
		missing = [f for f in required if f not in column_map]
		if missing:
			return {
				"success": False,
				"error": f"Missing required columns: {', '.join(missing)}",
				"column_map": column_map
			}
		
		# Preview: Match profiles to Items
		preview_data = []
		profile_col = column_map["profile"]
		unique_profiles = df[profile_col].dropna().unique()
		
		for profile in unique_profiles:
			# Search for matching item
			item = find_item_by_profile(cstr(profile).strip())
			preview_data.append({
				"profile": profile,
				"matched_item": item["name"] if item else None,
				"matched_item_name": item["item_name"] if item else None,
				"available_stock": item["stock"] if item else 0,
				"matched": bool(item)
			})
		
		# Create production orders
		created_orders = []
		errors = []
		
		for idx, row in df.iterrows():
			try:
				# Skip empty rows
				profile = cstr(row.get(column_map["profile"], "")).strip()
				if not profile:
					continue
				
				# Find item
				item = find_item_by_profile(profile)
				if not item:
					errors.append(f"Row {idx+2}: Profile '{profile}' not found in Item master")
					continue
				
				# Extract data
				drawing_num = cstr(row.get(column_map.get("drawing_number"), f"ITEM-{idx+1}")).strip()
				assembly = cstr(row.get(column_map.get("assembly"), "")).strip()
				item_name = cstr(row.get(column_map.get("item_name"), "")).strip()
				quantity = flt(row.get(column_map["quantity"], 1))
				weight = flt(row.get(column_map.get("weight"), 0))
				paint_spec = cstr(row.get(column_map.get("paint"), "")).strip()
				priority_val = cstr(row.get(column_map.get("priority"), "Medium")).strip()
				
				# Create Steel Production Order
				spo = frappe.new_doc("Steel Production Order")
				spo.customer = customer
				spo.item_code = item["name"]
				spo.drawing_number = drawing_num
				spo.assembly_mark = assembly
				spo.profile_section = profile
				spo.quantity = quantity
				spo.weight_per_unit = weight
				spo.paint_specification = paint_spec
				spo.lot_number = lot_number or cstr(row.get(column_map.get("lot"), "")).strip()
				spo.priority = map_priority(priority_val)
				
				# Add default production stages
				spo.append("production_stages", {"stage_name": "Fabrication", "stage_order": 1, "status": "Not Started"})
				spo.append("production_stages", {"stage_name": "Painting", "stage_order": 2, "status": "Not Started"})
				spo.append("production_stages", {"stage_name": "Dispatch", "stage_order": 3, "status": "Not Started"})
				spo.append("production_stages", {"stage_name": "Completed", "stage_order": 4, "status": "Not Started"})
				
				# Add material requirement
				spo.append("material_requirements", {
					"item": item["name"],
					"required_qty": quantity * weight if weight else 0,
					"uom": "Kg"
				})
				
				spo.insert()
				created_orders.append(spo.name)
				
			except Exception as e:
				errors.append(f"Row {idx+2}: {str(e)}")
		
		return {
			"success": True,
			"created_count": len(created_orders),
			"error_count": len(errors),
			"created_orders": created_orders,
			"errors": errors,
			"preview": preview_data,
			"column_map": column_map
		}
		
	except Exception as e:
		frappe.log_error(f"Excel import failed: {str(e)}", "Steel Production Import")
		return {
			"success": False,
			"error": str(e)
		}


def find_item_by_profile(profile_name):
	"""
	Find Item by profile/section name
	
	Args:
		profile_name: Profile name to search (e.g., UB203X133X25)
	
	Returns:
		dict: Item details or None
	"""
	if not profile_name:
		return None
	
	# Exact match on custom_profile_section
	items = frappe.get_all(
		"Item",
		filters={"custom_profile_section": profile_name},
		fields=["name", "item_name", "stock_uom"],
		limit=1
	)
	
	if items:
		item = items[0]
		# Get available stock
		stock_qty = frappe.db.sql("""
			SELECT SUM(actual_qty) 
			FROM `tabBin` 
			WHERE item_code = %s
		""", item["name"])
		
		item["stock"] = flt(stock_qty[0][0]) if stock_qty and stock_qty[0] else 0
		return item
	
	# Fallback: Search in item_name
	items = frappe.get_all(
		"Item",
		filters=[["item_name", "like", f"%{profile_name}%"]],
		fields=["name", "item_name", "stock_uom"],
		limit=1
	)
	
	if items:
		item = items[0]
		stock_qty = frappe.db.sql("""
			SELECT SUM(actual_qty) 
			FROM `tabBin` 
			WHERE item_code = %s
		""", item["name"])
		
		item["stock"] = flt(stock_qty[0][0]) if stock_qty and stock_qty[0] else 0
		return item
	
	return None


def map_priority(priority_str):
	"""Map priority string to standard values"""
	priority_lower = cstr(priority_str).lower()
	
	if any(word in priority_lower for word in ["urgent", "critical", "high"]):
		return "Urgent"
	elif any(word in priority_lower for word in ["low"]):
		return "Low"
	else:
		return "Medium"


@frappe.whitelist()
def preview_excel_import(file_path):
	"""
	Preview Excel import without creating records
	
	Args:
		file_path: Path to Excel or CSV file
	
	Returns:
		dict: Preview data with column mappings and profile matches
	"""
	try:
		# Read file
		if file_path.endswith('.csv'):
			df = pd.read_csv(file_path)
		else:
			df = pd.read_excel(file_path)
		
		# Map columns
		column_map = {}
		for field, possible_names in COLUMN_MAPPINGS.items():
			found_col = find_column(df, possible_names)
			if found_col:
				column_map[field] = found_col
		
		# Preview profiles
		preview_data = []
		if "profile" in column_map:
			profile_col = column_map["profile"]
			unique_profiles = df[profile_col].dropna().unique()
			
			for profile in unique_profiles:
				item = find_item_by_profile(cstr(profile).strip())
				preview_data.append({
					"profile": profile,
					"matched_item": item["name"] if item else None,
					"matched_item_name": item["item_name"] if item else None,
					"available_stock": item["stock"] if item else 0,
					"matched": bool(item)
				})
		
		return {
			"success": True,
			"total_rows": len(df),
			"column_map": column_map,
			"preview": preview_data
		}
		
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}
