"""
Steel Calculation Utilities
"""

import math
from frappe import _


# Steel density in kg/m³
STEEL_DENSITY = 7850


def calculate_plate_weight(length_mm, width_mm, thickness_mm):
    """
    Calculate weight of a steel plate
    
    Args:
        length_mm: Length in millimeters
        width_mm: Width in millimeters
        thickness_mm: Thickness in millimeters
    
    Returns:
        Weight in kilograms
    """
    # Convert to meters
    length = length_mm / 1000
    width = width_mm / 1000
    thickness = thickness_mm / 1000
    
    volume = length * width * thickness
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_round_bar_weight(diameter_mm, length_mm):
    """
    Calculate weight of a round bar
    
    Args:
        diameter_mm: Diameter in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    diameter = diameter_mm / 1000
    length = length_mm / 1000
    
    radius = diameter / 2
    volume = math.pi * radius * radius * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_pipe_weight(outer_diameter_mm, thickness_mm, length_mm):
    """
    Calculate weight of a hollow pipe
    
    Args:
        outer_diameter_mm: Outer diameter in millimeters
        thickness_mm: Wall thickness in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    outer_diameter = outer_diameter_mm / 1000
    thickness = thickness_mm / 1000
    length = length_mm / 1000
    
    outer_radius = outer_diameter / 2
    inner_radius = outer_radius - thickness
    
    volume = math.pi * (outer_radius**2 - inner_radius**2) * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_angle_weight(leg_a_mm, leg_b_mm, thickness_mm, length_mm):
    """
    Calculate weight of an angle section (L-shape)
    
    Args:
        leg_a_mm: First leg length in millimeters
        leg_b_mm: Second leg length in millimeters
        thickness_mm: Thickness in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    leg_a = leg_a_mm / 1000
    leg_b = leg_b_mm / 1000
    thickness = thickness_mm / 1000
    length = length_mm / 1000
    
    # Cross-sectional area (minus overlap at corner)
    area = (leg_a * thickness) + (leg_b * thickness) - (thickness * thickness)
    volume = area * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_channel_weight(web_width_mm, flange_height_mm, thickness_mm, length_mm):
    """
    Calculate weight of a channel section (C-shape)
    
    Args:
        web_width_mm: Web width in millimeters
        flange_height_mm: Flange height in millimeters
        thickness_mm: Thickness in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    web_width = web_width_mm / 1000
    flange_height = flange_height_mm / 1000
    thickness = thickness_mm / 1000
    length = length_mm / 1000
    
    # Cross-sectional area
    area = (web_width * thickness) + (2 * flange_height * thickness) - (2 * thickness * thickness)
    volume = area * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_beam_weight(height_mm, flange_width_mm, web_thickness_mm, flange_thickness_mm, length_mm):
    """
    Calculate weight of an I-beam (H-shape)
    
    Args:
        height_mm: Total height in millimeters
        flange_width_mm: Flange width in millimeters
        web_thickness_mm: Web thickness in millimeters
        flange_thickness_mm: Flange thickness in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    height = height_mm / 1000
    flange_width = flange_width_mm / 1000
    web_thickness = web_thickness_mm / 1000
    flange_thickness = flange_thickness_mm / 1000
    length = length_mm / 1000
    
    # Web height (excluding flanges)
    web_height = height - (2 * flange_thickness)
    
    # Cross-sectional area
    area = (2 * flange_width * flange_thickness) + (web_height * web_thickness)
    volume = area * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_square_bar_weight(side_mm, length_mm):
    """
    Calculate weight of a square bar
    
    Args:
        side_mm: Side length in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    side = side_mm / 1000
    length = length_mm / 1000
    
    volume = side * side * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_flat_bar_weight(width_mm, thickness_mm, length_mm):
    """
    Calculate weight of a flat bar
    
    Args:
        width_mm: Width in millimeters
        thickness_mm: Thickness in millimeters
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    width = width_mm / 1000
    thickness = thickness_mm / 1000
    length = length_mm / 1000
    
    volume = width * thickness * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def calculate_coil_weight(width_mm, thickness_mm, coil_outer_diameter_mm, coil_inner_diameter_mm):
    """
    Calculate weight of a steel coil
    
    Args:
        width_mm: Width of coil in millimeters
        thickness_mm: Sheet thickness in millimeters
        coil_outer_diameter_mm: Outer diameter of coil in millimeters
        coil_inner_diameter_mm: Inner diameter of coil in millimeters
    
    Returns:
        Weight in kilograms
    """
    width = width_mm / 1000
    thickness = thickness_mm / 1000
    outer_diameter = coil_outer_diameter_mm / 1000
    inner_diameter = coil_inner_diameter_mm / 1000
    
    # Calculate approximate length
    outer_radius = outer_diameter / 2
    inner_radius = inner_diameter / 2
    
    # Approximate number of wraps
    num_wraps = (outer_radius - inner_radius) / thickness
    
    # Average radius
    avg_radius = (outer_radius + inner_radius) / 2
    
    # Approximate length
    length = 2 * math.pi * avg_radius * num_wraps
    
    # Volume
    volume = width * thickness * length
    weight = volume * STEEL_DENSITY
    
    return round(weight, 3)


def mm_to_inch(mm):
    """Convert millimeters to inches"""
    return round(mm / 25.4, 3)


def inch_to_mm(inches):
    """Convert inches to millimeters"""
    return round(inches * 25.4, 3)


def kg_to_mt(kg):
    """Convert kilograms to metric tons"""
    return round(kg / 1000, 3)


def mt_to_kg(mt):
    """Convert metric tons to kilograms"""
    return round(mt * 1000, 3)


def feet_to_mm(feet):
    """Convert feet to millimeters"""
    return round(feet * 304.8, 2)


def mm_to_feet(mm):
    """Convert millimeters to feet"""
    return round(mm / 304.8, 3)


# Standard pipe sizes (NB to OD mapping in mm)
STANDARD_PIPE_SIZES = {
    "15NB": {"od": 21.3, "schedules": {"SCH40": 2.77, "SCH80": 3.73}},
    "20NB": {"od": 26.7, "schedules": {"SCH40": 2.87, "SCH80": 3.91}},
    "25NB": {"od": 33.4, "schedules": {"SCH40": 3.38, "SCH80": 4.55}},
    "32NB": {"od": 42.2, "schedules": {"SCH40": 3.56, "SCH80": 4.85}},
    "40NB": {"od": 48.3, "schedules": {"SCH40": 3.68, "SCH80": 5.08}},
    "50NB": {"od": 60.3, "schedules": {"SCH40": 3.91, "SCH80": 5.54}},
    "65NB": {"od": 73.0, "schedules": {"SCH40": 5.16, "SCH80": 7.01}},
    "80NB": {"od": 88.9, "schedules": {"SCH40": 5.49, "SCH80": 7.62}},
    "100NB": {"od": 114.3, "schedules": {"SCH40": 6.02, "SCH80": 8.56}},
    "125NB": {"od": 141.3, "schedules": {"SCH40": 6.55, "SCH80": 9.53}},
    "150NB": {"od": 168.3, "schedules": {"SCH40": 7.11, "SCH80": 10.97}},
    "200NB": {"od": 219.1, "schedules": {"SCH40": 8.18, "SCH80": 12.70}},
    "250NB": {"od": 273.1, "schedules": {"SCH40": 9.27, "SCH80": 15.09}},
    "300NB": {"od": 323.8, "schedules": {"SCH40": 9.53, "SCH80": 17.48}},
}


def get_standard_pipe_weight(nb_size, schedule, length_mm):
    """
    Get weight of a standard pipe size
    
    Args:
        nb_size: Nominal bore size (e.g., "50NB")
        schedule: Pipe schedule (e.g., "SCH40")
        length_mm: Length in millimeters
    
    Returns:
        Weight in kilograms
    """
    if nb_size not in STANDARD_PIPE_SIZES:
        return None
    
    pipe_data = STANDARD_PIPE_SIZES[nb_size]
    if schedule not in pipe_data["schedules"]:
        return None
    
    od = pipe_data["od"]
    thickness = pipe_data["schedules"][schedule]
    
    return calculate_pipe_weight(od, thickness, length_mm)
