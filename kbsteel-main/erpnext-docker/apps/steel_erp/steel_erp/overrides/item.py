"""
Custom Item Class for Steel ERP
"""

import frappe
from erpnext.stock.doctype.item.item import Item


class SteelItem(Item):
    """Extended Item class with steel-specific functionality"""
    
    def validate(self):
        """Validate with steel-specific checks"""
        super().validate()
        
        # Auto-calculate weight if dimensions provided
        if self.steel_type:
            self.calculate_weight()
            self.validate_dimensions()
    
    def calculate_weight(self):
        """Calculate weight based on dimensions"""
        from steel_erp.utils.steel_calculations import (
            calculate_plate_weight,
            calculate_round_bar_weight,
            calculate_pipe_weight,
            calculate_flat_bar_weight,
            calculate_square_bar_weight
        )
        
        shape = self.get("material_shape")
        length = self.get("steel_length") or 0
        width = self.get("steel_width") or 0
        thickness = self.get("steel_thickness") or 0
        diameter = self.get("steel_diameter") or 0
        
        weight = 0
        
        if shape == "Plate" and length and width and thickness:
            weight = calculate_plate_weight(length, width, thickness)
            
        elif shape == "Sheet" and length and width and thickness:
            weight = calculate_plate_weight(length, width, thickness)
            
        elif shape == "Round" and diameter and length:
            weight = calculate_round_bar_weight(diameter, length)
            
        elif shape == "Pipe" and diameter and thickness and length:
            weight = calculate_pipe_weight(diameter, thickness, length)
            
        elif shape == "Flat" and width and thickness and length:
            weight = calculate_flat_bar_weight(width, thickness, length)
            
        elif shape == "Square" and width and length:
            weight = calculate_square_bar_weight(width, length)
        
        if weight > 0:
            self.weight_per_unit = weight
    
    def validate_dimensions(self):
        """Validate steel dimensions"""
        shape = self.get("material_shape")
        
        # Validate based on shape
        if shape == "Pipe":
            if not self.get("steel_diameter"):
                frappe.msgprint("Diameter is recommended for pipe items", indicator="orange")
            if not self.get("steel_thickness"):
                frappe.msgprint("Wall thickness is recommended for pipe items", indicator="orange")
                
        elif shape in ["Plate", "Sheet"]:
            if not self.get("steel_thickness"):
                frappe.msgprint("Thickness is recommended for plate/sheet items", indicator="orange")
                
        elif shape == "Round":
            if not self.get("steel_diameter"):
                frappe.msgprint("Diameter is recommended for round bar items", indicator="orange")
    
    def get_steel_description(self):
        """Generate steel-specific description"""
        parts = []
        
        if self.get("steel_type"):
            parts.append(self.steel_type)
        
        if self.get("material_shape"):
            parts.append(self.material_shape)
        
        if self.get("steel_grade"):
            parts.append(f"Grade: {self.steel_grade}")
        
        # Add dimensions
        dims = []
        if self.get("steel_diameter"):
            dims.append(f"Ø{self.steel_diameter}mm")
        if self.get("steel_thickness"):
            dims.append(f"T:{self.steel_thickness}mm")
        if self.get("steel_width"):
            dims.append(f"W:{self.steel_width}mm")
        if self.get("steel_length"):
            dims.append(f"L:{self.steel_length}mm")
        
        if dims:
            parts.append(" × ".join(dims))
        
        if self.get("weight_per_unit"):
            parts.append(f"Weight: {self.weight_per_unit} KG")
        
        return " | ".join(parts)
