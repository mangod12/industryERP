"""
Custom Stock Entry Class for Steel ERP
"""

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class SteelStockEntry(StockEntry):
    """Extended Stock Entry class with steel-specific functionality"""
    
    def validate(self):
        """Validate with steel-specific checks"""
        super().validate()
        
        # Validate steel items
        self.validate_steel_items()
        self.calculate_total_weight()
    
    def validate_steel_items(self):
        """Validate steel-specific fields"""
        for item in self.items:
            steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
            
            if steel_type:
                # Check heat number for material receipt
                if self.stock_entry_type == "Material Receipt":
                    if not item.get("heat_number"):
                        frappe.msgprint(
                            f"Row {item.idx}: Heat number recommended for {item.item_code}",
                            indicator="orange"
                        )
    
    def calculate_total_weight(self):
        """Calculate total weight of steel items"""
        total_weight = 0
        
        for item in self.items:
            weight_per_unit = frappe.db.get_value("Item", item.item_code, "weight_per_unit")
            if weight_per_unit:
                total_weight += weight_per_unit * item.qty
        
        # Store in custom field if exists
        if hasattr(self, 'total_weight'):
            self.total_weight = round(total_weight, 3)
    
    def on_submit(self):
        """Actions on submit"""
        super().on_submit()
        
        # Log steel movements
        self.log_steel_movement()
    
    def log_steel_movement(self):
        """Create log for steel material movements"""
        steel_items = []
        
        for item in self.items:
            steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
            
            if steel_type:
                steel_items.append({
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "from_warehouse": item.s_warehouse,
                    "to_warehouse": item.t_warehouse,
                    "heat_number": item.get("heat_number"),
                    "mill_tc_number": item.get("mill_tc_number")
                })
        
        if steel_items:
            frappe.log_error(
                message=str({
                    "stock_entry": self.name,
                    "entry_type": self.stock_entry_type,
                    "posting_date": str(self.posting_date),
                    "items": steel_items
                }),
                title=f"Steel Stock Movement: {self.name}"
            )
