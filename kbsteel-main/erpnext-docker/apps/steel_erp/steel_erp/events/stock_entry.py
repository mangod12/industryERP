"""
Stock Entry Events for Steel ERP
Handles steel-specific stock operations
"""

import frappe
from frappe import _
from frappe.utils import now, nowdate


def validate_stock_entry(doc, method):
    """Validate steel-specific fields in stock entry"""
    
    for item in doc.items:
        # Get item details
        item_doc = frappe.get_cached_doc("Item", item.item_code)
        
        # Check if it's a steel item
        steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
        
        if steel_type:
            # Validate heat number for raw materials
            if doc.stock_entry_type == "Material Receipt":
                if not item.get("heat_number"):
                    frappe.msgprint(
                        _("Row {0}: Heat Number recommended for steel item {1}").format(
                            item.idx, item.item_code
                        ),
                        indicator="orange"
                    )


def on_submit_stock_entry(doc, method):
    """Actions after stock entry submission"""
    
    # Log stock movement for steel tracking
    for item in doc.items:
        steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
        
        if steel_type:
            create_steel_movement_log(doc, item)


def create_steel_movement_log(doc, item):
    """Create a log entry for steel material movement"""
    
    # This can be used for traceability
    log_data = {
        "item_code": item.item_code,
        "stock_entry": doc.name,
        "stock_entry_type": doc.stock_entry_type,
        "qty": item.qty,
        "from_warehouse": item.s_warehouse,
        "to_warehouse": item.t_warehouse,
        "heat_number": item.get("heat_number"),
        "posting_date": doc.posting_date,
        "posting_time": doc.posting_time
    }
    
    # Store in custom log if needed
    frappe.log_error(
        message=str(log_data),
        title=f"Steel Movement: {item.item_code}"
    )


def calculate_steel_weight(doc, method):
    """Auto-calculate weight based on dimensions"""
    
    for item in doc.items:
        item_doc = frappe.get_cached_doc("Item", item.item_code)
        
        # Get steel dimensions
        length = frappe.db.get_value("Item", item.item_code, "steel_length") or 0
        width = frappe.db.get_value("Item", item.item_code, "steel_width") or 0
        thickness = frappe.db.get_value("Item", item.item_code, "steel_thickness") or 0
        diameter = frappe.db.get_value("Item", item.item_code, "steel_diameter") or 0
        shape = frappe.db.get_value("Item", item.item_code, "material_shape")
        
        if shape and any([length, width, thickness, diameter]):
            # Steel density: 7850 kg/m³
            density = 7850
            
            calculated_weight = 0
            
            if shape == "Plate" and length and width and thickness:
                # Volume in m³
                volume = (length / 1000) * (width / 1000) * (thickness / 1000)
                calculated_weight = volume * density
                
            elif shape == "Round" and diameter and length:
                import math
                radius = (diameter / 2) / 1000
                volume = math.pi * radius * radius * (length / 1000)
                calculated_weight = volume * density
                
            elif shape == "Pipe" and diameter and thickness and length:
                import math
                outer_radius = (diameter / 2) / 1000
                inner_radius = ((diameter - 2 * thickness) / 2) / 1000
                volume = math.pi * (outer_radius**2 - inner_radius**2) * (length / 1000)
                calculated_weight = volume * density
            
            if calculated_weight > 0:
                # Update weight per unit in item
                frappe.db.set_value("Item", item.item_code, "weight_per_unit", round(calculated_weight, 3))
