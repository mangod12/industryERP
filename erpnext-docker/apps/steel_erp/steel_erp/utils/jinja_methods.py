"""
Jinja Template Utilities for Steel ERP
"""

from .steel_calculations import (
    calculate_plate_weight,
    calculate_round_bar_weight,
    calculate_pipe_weight,
    calculate_angle_weight,
    calculate_beam_weight,
    mm_to_inch,
    kg_to_mt,
    feet_to_mm,
    get_standard_pipe_weight
)


def format_steel_dimensions(item):
    """Format steel dimensions for display"""
    
    dimensions = []
    
    if item.get("steel_diameter"):
        dimensions.append(f"Ø{item.steel_diameter}mm")
    
    if item.get("steel_length"):
        dimensions.append(f"L:{item.steel_length}mm")
    
    if item.get("steel_width"):
        dimensions.append(f"W:{item.steel_width}mm")
    
    if item.get("steel_thickness"):
        dimensions.append(f"T:{item.steel_thickness}mm")
    
    return " × ".join(dimensions) if dimensions else "-"


def format_weight(weight_kg):
    """Format weight with appropriate unit"""
    
    if weight_kg >= 1000:
        return f"{kg_to_mt(weight_kg)} MT"
    else:
        return f"{round(weight_kg, 2)} KG"


def get_steel_grade_display(grade_code):
    """Get descriptive name for steel grade"""
    
    grades = {
        "IS2062 E250": "IS 2062 Grade E250 (Mild Steel)",
        "IS2062 E350": "IS 2062 Grade E350 (High Strength)",
        "IS2062 E410": "IS 2062 Grade E410 (Higher Strength)",
        "SAIL MA 250": "SAIL MA 250 (Structural Steel)",
        "SAIL MA 350": "SAIL MA 350 (High Strength Structural)",
        "SAIL MA 410": "SAIL MA 410 (Earthquake Resistant)",
        "SS304": "Stainless Steel 304 (Food Grade)",
        "SS316": "Stainless Steel 316 (Marine Grade)",
        "SS202": "Stainless Steel 202 (Economy Grade)"
    }
    
    return grades.get(grade_code, grade_code)


def get_tracking_url(tracking_code):
    """Generate tracking URL for a tracking code"""
    return f"/tracking?code={tracking_code}"
