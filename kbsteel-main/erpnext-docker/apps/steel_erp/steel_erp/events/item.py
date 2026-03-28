"""
Item Events for Steel ERP
Handles item creation and validation for steel materials
"""

import frappe
from frappe import _


def validate_item(doc, method):
    """Validate steel-specific fields in item"""
    
    # Auto-set item group based on steel type
    if doc.get("steel_type") and doc.get("material_shape"):
        auto_set_item_group(doc)
    
    # Validate dimensions
    validate_steel_dimensions(doc)
    
    # Calculate weight if dimensions provided
    calculate_item_weight(doc)


def auto_set_item_group(doc):
    """Auto-set item group based on steel type and shape"""
    
    steel_type = doc.get("steel_type")
    shape = doc.get("material_shape")
    
    if not steel_type or not shape:
        return
    
    # Map steel types to item groups
    group_mapping = {
        ("Mild Steel (MS)", "Pipe"): "MS Pipes",
        ("Mild Steel (MS)", "Plate"): "MS Plates",
        ("Mild Steel (MS)", "Beam"): "MS Beams",
        ("Mild Steel (MS)", "Angle"): "MS Angles",
        ("Mild Steel (MS)", "Channel"): "MS Channels",
        ("Mild Steel (MS)", "Round"): "MS Rounds",
        ("Mild Steel (MS)", "Square"): "MS Squares",
        ("Mild Steel (MS)", "Flat"): "MS Flats",
        ("Galvanized Iron (GI)", "Pipe"): "GI Pipes",
        ("Galvanized Iron (GI)", "Sheet"): "GI Sheets",
        ("Hot Rolled (HR)", "Coil"): "HR Coils",
        ("Hot Rolled (HR)", "Sheet"): "HR Sheets",
        ("Cold Rolled (CR)", "Coil"): "CR Coils",
        ("Cold Rolled (CR)", "Sheet"): "CR Sheets",
    }
    
    key = (steel_type, shape)
    if key in group_mapping:
        group_name = group_mapping[key]
        if frappe.db.exists("Item Group", group_name):
            doc.item_group = group_name


def validate_steel_dimensions(doc):
    """Validate that steel dimensions are within acceptable ranges"""
    
    if not doc.get("steel_type"):
        return
    
    length = doc.get("steel_length") or 0
    width = doc.get("steel_width") or 0
    thickness = doc.get("steel_thickness") or 0
    diameter = doc.get("steel_diameter") or 0
    shape = doc.get("material_shape")
    
    # Validate based on shape
    if shape == "Pipe":
        if diameter and diameter > 1000:
            frappe.msgprint(
                _("Pipe diameter {0}mm seems unusually large. Please verify.").format(diameter),
                indicator="orange"
            )
        if thickness and thickness > 50:
            frappe.msgprint(
                _("Pipe thickness {0}mm seems unusually large. Please verify.").format(thickness),
                indicator="orange"
            )
    
    elif shape == "Plate":
        if thickness and thickness > 100:
            frappe.msgprint(
                _("Plate thickness {0}mm seems unusually large. Please verify.").format(thickness),
                indicator="orange"
            )
    
    # Length validation (standard lengths in steel industry)
    if length:
        standard_lengths = [6000, 6100, 12000, 12200]  # in mm
        if length not in standard_lengths and length > 100:
            frappe.msgprint(
                _("Non-standard length {0}mm. Standard lengths are {1}").format(
                    length, ", ".join([str(l) for l in standard_lengths])
                ),
                indicator="blue"
            )


def calculate_item_weight(doc):
    """Calculate weight per unit based on dimensions"""
    
    if not doc.get("steel_type"):
        return
    
    length = (doc.get("steel_length") or 0) / 1000  # Convert to meters
    width = (doc.get("steel_width") or 0) / 1000
    thickness = (doc.get("steel_thickness") or 0) / 1000
    diameter = (doc.get("steel_diameter") or 0) / 1000
    shape = doc.get("material_shape")
    
    # Steel density: 7850 kg/m³
    density = 7850
    weight = 0
    
    if shape == "Plate" and length and width and thickness:
        volume = length * width * thickness
        weight = volume * density
        
    elif shape == "Sheet" and length and width and thickness:
        volume = length * width * thickness
        weight = volume * density
        
    elif shape == "Round" and diameter and length:
        import math
        radius = diameter / 2
        volume = math.pi * radius * radius * length
        weight = volume * density
        
    elif shape == "Pipe" and diameter and thickness and length:
        import math
        outer_radius = diameter / 2
        inner_radius = (diameter - 2 * (thickness * 1000 / 1000)) / 2
        volume = math.pi * (outer_radius**2 - inner_radius**2) * length
        weight = volume * density
        
    elif shape == "Angle" and length and width and thickness:
        # L-shape calculation (simplified)
        volume = (2 * width * thickness - thickness * thickness) * length
        weight = volume * density
        
    elif shape == "Channel" and length and width and thickness:
        # U-shape calculation (simplified)
        height = doc.get("steel_height") or width  # Use width as default height
        volume = (width * thickness + 2 * height * thickness) * length
        weight = volume * density
    
    if weight > 0:
        doc.weight_per_unit = round(weight, 3)


def on_update_item(doc, method):
    """Actions after item update"""
    
    # Update related stock entries if dimensions changed
    pass


def validate_item_name(doc, method):
    """Auto-generate descriptive item name for steel products"""
    
    if not doc.get("steel_type"):
        return
    
    # Don't override if name is already set
    if doc.item_name and not doc.item_name.startswith("New Item"):
        return
    
    parts = []
    
    # Add steel type
    steel_type = doc.get("steel_type", "").replace("(", "").replace(")", "")
    if steel_type:
        parts.append(steel_type)
    
    # Add shape
    if doc.get("material_shape"):
        parts.append(doc.material_shape)
    
    # Add grade
    if doc.get("steel_grade"):
        parts.append(doc.steel_grade)
    
    # Add key dimension
    if doc.get("steel_diameter"):
        parts.append(f"Ø{doc.steel_diameter}mm")
    elif doc.get("steel_thickness"):
        parts.append(f"{doc.steel_thickness}mm")
    
    if parts:
        doc.item_name = " ".join(parts)
