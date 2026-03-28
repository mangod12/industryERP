"""
Purchase Receipt Events for Steel ERP
Handles GRN (Goods Receipt Note) for steel materials
"""

import frappe
from frappe import _
from frappe.utils import flt


def validate_purchase_receipt(doc, method):
    """Validate steel-specific fields in purchase receipt"""
    
    for item in doc.items:
        steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
        
        if steel_type:
            # Validate heat number for traceability
            if not item.get("heat_number"):
                frappe.msgprint(
                    _("Row {0}: Heat Number recommended for steel item {1}").format(
                        item.idx, item.item_code
                    ),
                    indicator="orange"
                )
            
            # Calculate weight difference if both weights provided
            calculate_weight_difference(item)


def calculate_weight_difference(item):
    """Calculate difference between mill weight and actual weight"""
    
    mill_weight = flt(item.get("mill_weight", 0))
    actual_weight = flt(item.get("actual_weight", 0))
    
    if mill_weight and actual_weight:
        difference = actual_weight - mill_weight
        item.weight_difference = difference
        
        # Alert if difference is significant (> 2%)
        if mill_weight > 0:
            diff_percent = abs(difference / mill_weight * 100)
            if diff_percent > 2:
                frappe.msgprint(
                    _("Row {0}: Weight difference of {1}% detected for {2}").format(
                        item.idx, round(diff_percent, 2), item.item_code
                    ),
                    indicator="orange"
                )


def on_submit_purchase_receipt(doc, method):
    """Actions after purchase receipt submission"""
    
    # Create GRN log for steel materials
    create_grn_log(doc)


def create_grn_log(doc):
    """Create GRN log for tracking"""
    
    steel_items = []
    
    for item in doc.items:
        steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
        
        if steel_type:
            steel_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "heat_number": item.get("heat_number"),
                "mill_weight": item.get("mill_weight"),
                "actual_weight": item.get("actual_weight"),
                "weight_difference": item.get("weight_difference"),
                "warehouse": item.warehouse
            })
    
    if steel_items:
        grn_data = {
            "purchase_receipt": doc.name,
            "supplier": doc.supplier,
            "posting_date": doc.posting_date,
            "bill_no": doc.bill_no,
            "total_qty": sum([i["qty"] for i in steel_items]),
            "total_amount": sum([i["amount"] for i in steel_items]),
            "steel_items": steel_items
        }
        
        frappe.log_error(
            message=str(grn_data),
            title=f"Steel GRN: {doc.name}"
        )


def validate_supplier_quality(doc, method):
    """Validate supplier quality rating"""
    
    # Check supplier's historical quality
    supplier_quality = get_supplier_quality_score(doc.supplier)
    
    if supplier_quality and supplier_quality < 3:
        frappe.msgprint(
            _("Note: Supplier {0} has a low quality rating ({1}/5). Extra QC recommended.").format(
                doc.supplier, supplier_quality
            ),
            indicator="orange"
        )


def get_supplier_quality_score(supplier):
    """Get supplier's quality score based on historical data"""
    
    # Count quality issues
    quality_issues = frappe.db.count(
        "Purchase Receipt",
        filters={
            "supplier": supplier,
            "docstatus": 1
        }
    )
    
    # This is a simplified scoring - real implementation would track actual quality issues
    return 4  # Default good score


def on_cancel_purchase_receipt(doc, method):
    """Handle cancellation"""
    
    frappe.log_error(
        message=f"Purchase Receipt {doc.name} cancelled by {frappe.session.user}",
        title=f"GRN Cancelled: {doc.name}"
    )
