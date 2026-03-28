"""
Scheduled Tasks for Steel ERP
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, getdate


def daily():
    """Daily scheduled tasks"""
    check_low_stock_alerts()
    send_pending_delivery_reminders()
    update_overdue_deliveries()


def weekly():
    """Weekly scheduled tasks"""
    generate_weekly_stock_report()
    cleanup_old_logs()


def check_low_stock_alerts():
    """Check and alert for low stock items"""
    
    # Get all steel items with reorder level
    items = frappe.db.sql("""
        SELECT 
            item.item_code,
            item.item_name,
            item.steel_type,
            bin.actual_qty,
            bin.warehouse,
            item.reorder_level
        FROM `tabItem` item
        JOIN `tabBin` bin ON bin.item_code = item.item_code
        WHERE item.steel_type IS NOT NULL
        AND item.reorder_level > 0
        AND bin.actual_qty <= item.reorder_level
    """, as_dict=True)
    
    if items:
        # Create low stock alert
        alert_content = "Low Stock Alert for Steel Items:\n\n"
        
        for item in items:
            alert_content += f"- {item.item_code}: {item.actual_qty} in {item.warehouse} (Reorder Level: {item.reorder_level})\n"
        
        frappe.log_error(
            message=alert_content,
            title=f"Low Stock Alert - {nowdate()}"
        )
        
        # Send notification to Stock Manager
        send_stock_alert_notification(items)


def send_stock_alert_notification(items):
    """Send notification for low stock"""
    
    # Get users with Stock Manager role
    stock_managers = frappe.get_all(
        "Has Role",
        filters={"role": "Stock Manager"},
        pluck="parent"
    )
    
    if stock_managers:
        subject = f"Low Stock Alert - {len(items)} items below reorder level"
        message = "The following steel items are below reorder level:\n\n"
        
        for item in items:
            message += f"• {item.item_name} ({item.item_code}): {item.actual_qty} units\n"
        
        for user in stock_managers:
            try:
                frappe.sendmail(
                    recipients=user,
                    subject=subject,
                    message=message
                )
            except Exception as e:
                frappe.log_error(f"Failed to send email to {user}: {e}")


def send_pending_delivery_reminders():
    """Send reminders for pending deliveries"""
    
    # Get delivery notes due today or overdue
    pending_deliveries = frappe.db.sql("""
        SELECT 
            name,
            customer,
            posting_date,
            grand_total,
            lr_number,
            vehicle_no
        FROM `tabDelivery Note`
        WHERE docstatus = 1
        AND status = 'To Bill'
        AND posting_date <= %s
    """, (nowdate(),), as_dict=True)
    
    if pending_deliveries:
        frappe.log_error(
            message=str(pending_deliveries),
            title=f"Pending Deliveries - {nowdate()}"
        )


def update_overdue_deliveries():
    """Update status of overdue deliveries"""
    
    # This would update custom fields for tracking overdue deliveries
    pass


def generate_weekly_stock_report():
    """Generate weekly stock movement report"""
    
    from_date = add_days(nowdate(), -7)
    
    # Get stock movements
    movements = frappe.db.sql("""
        SELECT 
            item_code,
            warehouse,
            SUM(actual_qty) as total_qty,
            SUM(IF(actual_qty > 0, actual_qty, 0)) as in_qty,
            SUM(IF(actual_qty < 0, ABS(actual_qty), 0)) as out_qty
        FROM `tabStock Ledger Entry`
        WHERE posting_date BETWEEN %s AND %s
        GROUP BY item_code, warehouse
    """, (from_date, nowdate()), as_dict=True)
    
    if movements:
        report_content = f"Weekly Stock Movement Report ({from_date} to {nowdate()})\n\n"
        
        for m in movements:
            report_content += f"- {m.item_code} @ {m.warehouse}: IN {m.in_qty}, OUT {m.out_qty}\n"
        
        frappe.log_error(
            message=report_content,
            title=f"Weekly Stock Report - {nowdate()}"
        )


def cleanup_old_logs():
    """Cleanup old error logs"""
    
    # Delete logs older than 30 days
    cutoff_date = add_days(nowdate(), -30)
    
    frappe.db.sql("""
        DELETE FROM `tabError Log`
        WHERE creation < %s
        AND title LIKE 'Steel%%'
    """, (cutoff_date,))
    
    frappe.db.commit()
