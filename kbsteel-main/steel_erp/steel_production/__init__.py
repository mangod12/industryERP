"""Steel Production Module"""

import frappe


def on_stage_change(doc, method):
	"""Hook called when Steel Production Order is updated"""
	# Send notifications based on stage changes
	send_stage_notifications(doc)


def on_production_submit(doc, method):
	"""Hook called when Steel Production Order is submitted"""
	# Initialize default stages if not present
	if not doc.production_stages:
		doc.add_default_stages()
		doc.save()


def send_stage_notifications(doc):
	"""Send notifications when production stages change"""
	# Get users who should be notified
	recipients = get_notification_recipients(doc)
	
	if not recipients:
		return
	
	# Create notification
	for recipient in recipients:
		frappe.get_doc({
			"doctype": "Notification Log",
			"subject": f"Production Update: {doc.name}",
			"for_user": recipient,
			"type": "Alert",
			"document_type": doc.doctype,
			"document_name": doc.name,
			"email_content": f"Status: {doc.status}, Current Stage: {doc.current_stage}"
		}).insert(ignore_permissions=True)


def get_notification_recipients(doc):
	"""Get list of users to notify about production updates"""
	recipients = []
	
	# Notify Manufacturing Managers
	managers = frappe.get_all(
		"Has Role",
		filters={"role": "Manufacturing Manager", "parenttype": "User"},
		fields=["parent"]
	)
	recipients.extend([m.parent for m in managers])
	
	return list(set(recipients))  # Remove duplicates


def create_material_stock_entry(production_order):
	"""Create Stock Entry for material consumption (Material Issue)"""
	if not production_order.material_requirements:
		frappe.throw("No material requirements defined for this production order")
	
	# Create Stock Entry
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Issue"
	stock_entry.company = frappe.defaults.get_defaults().get("company")
	stock_entry.posting_date = frappe.utils.today()
	stock_entry.posting_time = frappe.utils.nowtime()
	
	# Add reference to production order
	stock_entry.custom_steel_production_order = production_order.name
	
	# Add items from material requirements
	for material in production_order.material_requirements:
		stock_entry.append("items", {
			"item_code": material.item,
			"qty": material.required_qty,
			"uom": material.uom or "Kg",
			"s_warehouse": material.warehouse or get_default_warehouse(),
			"batch_no": material.batch if material.batch else None,
			"expense_account": get_expense_account(),
			"cost_center": get_default_cost_center()
		})
	
	stock_entry.insert()
	stock_entry.submit()
	
	return stock_entry.name


def get_default_warehouse():
	"""Get default warehouse for material issue"""
	warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
	if not warehouse:
		warehouses = frappe.get_all("Warehouse", limit=1)
		if warehouses:
			warehouse = warehouses[0].name
	return warehouse


def get_expense_account():
	"""Get default expense account for material consumption"""
	company = frappe.defaults.get_defaults().get("company")
	expense_account = frappe.db.get_value(
		"Company",
		company,
		"default_expense_account"
	)
	return expense_account


def get_default_cost_center():
	"""Get default cost center"""
	company = frappe.defaults.get_defaults().get("company")
	cost_center = frappe.db.get_value(
		"Company",
		company,
		"cost_center"
	)
	return cost_center
