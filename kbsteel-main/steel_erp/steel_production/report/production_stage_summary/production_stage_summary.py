# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "production_order",
			"label": _("Production Order"),
			"fieldtype": "Link",
			"options": "Steel Production Order",
			"width": 180
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "drawing_number",
			"label": _("Drawing Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "profile_section",
			"label": _("Profile"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "total_weight",
			"label": _("Weight (kg)"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "current_stage",
			"label": _("Current Stage"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "completion",
			"label": _("Completion %"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "fabrication_status",
			"label": _("Fabrication"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "painting_status",
			"label": _("Painting"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "dispatch_status",
			"label": _("Dispatch"),
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT 
			spo.name as production_order,
			spo.customer,
			spo.drawing_number,
			spo.profile_section,
			spo.quantity,
			spo.total_weight,
			spo.current_stage,
			spo.status,
			spo.overall_completion as completion,
			(SELECT ps1.status FROM `tabProduction Stage` ps1 
			 WHERE ps1.parent = spo.name AND ps1.stage_name = 'Fabrication' LIMIT 1) as fabrication_status,
			(SELECT ps2.status FROM `tabProduction Stage` ps2 
			 WHERE ps2.parent = spo.name AND ps2.stage_name = 'Painting' LIMIT 1) as painting_status,
			(SELECT ps3.status FROM `tabProduction Stage` ps3 
			 WHERE ps3.parent = spo.name AND ps3.stage_name = 'Dispatch' LIMIT 1) as dispatch_status
		FROM `tabSteel Production Order` spo
		WHERE spo.docstatus = 1
		{conditions}
		ORDER BY spo.posting_date DESC, spo.name
	""", as_dict=1)
	
	return data


def get_conditions(filters):
	conditions = []
	
	if filters.get("customer"):
		conditions.append(f"AND spo.customer = '{filters.get('customer')}'")
	
	if filters.get("status"):
		conditions.append(f"AND spo.status = '{filters.get('status')}'")
	
	if filters.get("current_stage"):
		conditions.append(f"AND spo.current_stage = '{filters.get('current_stage')}'")
	
	if filters.get("from_date"):
		conditions.append(f"AND spo.posting_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"AND spo.posting_date <= '{filters.get('to_date')}'")
	
	return " ".join(conditions)
