"""
Delivery Note Events for Steel ERP
Handles dispatch tracking and vehicle details
"""

import frappe
from frappe import _
from frappe.utils import now, nowdate, random_string
import hashlib
import time


def generate_tracking_code(doc, method):
    """Generate unique tracking codes for delivery items"""
    
    for item in doc.items:
        if not item.get("tracking_code"):
            # Generate unique tracking code
            base_string = f"{doc.name}-{item.item_code}-{item.idx}-{time.time()}"
            hash_object = hashlib.md5(base_string.encode())
            tracking_code = f"KB-{hash_object.hexdigest()[:8].upper()}"
            
            item.tracking_code = tracking_code


def validate_delivery_note(doc, method):
    """Validate delivery note fields"""
    
    # Generate tracking codes
    generate_tracking_code(doc, method)
    
    # Validate transport details if shipping
    if doc.is_return == 0:
        if not doc.get("vehicle_no"):
            frappe.msgprint(
                _("Vehicle Number is recommended for dispatch tracking"),
                indicator="orange"
            )


def on_submit_delivery_note(doc, method):
    """Actions after delivery note submission"""
    
    # Log dispatch for tracking
    create_dispatch_log(doc)
    
    # Send SMS notification if configured
    send_dispatch_notification(doc)


def create_dispatch_log(doc):
    """Create dispatch tracking log"""
    
    dispatch_data = {
        "delivery_note": doc.name,
        "customer": doc.customer,
        "posting_date": doc.posting_date,
        "vehicle_no": doc.get("vehicle_no"),
        "driver_name": doc.get("driver_name"),
        "driver_mobile": doc.get("driver_mobile"),
        "transporter": doc.get("transporter"),
        "lr_number": doc.get("lr_number"),
        "total_qty": sum([item.qty for item in doc.items]),
        "total_amount": doc.grand_total,
        "items": [
            {
                "item_code": item.item_code,
                "qty": item.qty,
                "tracking_code": item.get("tracking_code"),
                "heat_number": item.get("heat_number")
            }
            for item in doc.items
        ]
    }
    
    # Log for audit trail
    frappe.log_error(
        message=str(dispatch_data),
        title=f"Steel Dispatch: {doc.name}"
    )


def send_dispatch_notification(doc):
    """Send SMS/Email notification for dispatch"""
    
    # Get customer contact
    customer_mobile = frappe.db.get_value("Customer", doc.customer, "mobile_no")
    
    if customer_mobile and doc.get("vehicle_no"):
        message = f"""
Kumar Brothers Steel - Dispatch Alert
DN: {doc.name}
Vehicle: {doc.get('vehicle_no', 'N/A')}
Driver: {doc.get('driver_name', 'N/A')}
Contact: {doc.get('driver_mobile', 'N/A')}
Items: {len(doc.items)} materials dispatched
        """.strip()
        
        # Log the notification (actual SMS sending would be configured separately)
        frappe.log_error(
            message=f"To: {customer_mobile}\n\n{message}",
            title=f"Dispatch SMS: {doc.name}"
        )


def validate_steel_items(doc, method):
    """Validate steel-specific details in delivery items"""
    
    for item in doc.items:
        steel_type = frappe.db.get_value("Item", item.item_code, "steel_type")
        
        if steel_type:
            # Validate stock availability with heat number
            if item.get("heat_number"):
                validate_heat_number_stock(item)


def validate_heat_number_stock(item):
    """Validate that heat number has sufficient stock"""
    # This would connect to batch/serial number tracking
    pass


def on_cancel_delivery_note(doc, method):
    """Handle cancellation of delivery note"""
    
    frappe.log_error(
        message=f"Delivery Note {doc.name} cancelled by {frappe.session.user}",
        title=f"DN Cancelled: {doc.name}"
    )
