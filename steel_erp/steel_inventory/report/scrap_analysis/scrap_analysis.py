# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_report_summary(data)
	
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "scrap_record",
			"label": _("Scrap Record"),
			"fieldtype": "Link",
			"options": "Scrap Record",
			"width": 150
		},
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "material_item",
			"label": _("Material"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "weight_kg",
			"label": _("Weight (kg)"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 3
		},
		{
			"fieldname": "reason_code",
			"label": _("Reason"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "recoverable",
			"label": _("Recoverable"),
			"fieldtype": "Check",
			"width": 80
		},
		{
			"fieldname": "estimated_loss",
			"label": _("Est. Loss Value"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "recovery_value",
			"label": _("Recovery Value"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "net_loss",
			"label": _("Net Loss"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "source_production_order",
			"label": _("Production Order"),
			"fieldtype": "Link",
			"options": "Steel Production Order",
			"width": 150
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT 
			name as scrap_record,
			posting_date,
			material_item,
			weight_kg,
			reason_code,
			recoverable,
			estimated_loss_value as estimated_loss,
			recovery_value,
			net_loss_value as net_loss,
			source_production_order
		FROM `tabScrap Record`
		WHERE docstatus = 1
		{conditions}
		ORDER BY posting_date DESC
	""", as_dict=1)
	
	return data


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append(f"AND posting_date >= '{filters.get('from_date')}'")
	
	if filters.get("to_date"):
		conditions.append(f"AND posting_date <= '{filters.get('to_date')}'")
	
	if filters.get("material_item"):
		conditions.append(f"AND material_item = '{filters.get('material_item')}'")
	
	if filters.get("reason_code"):
		conditions.append(f"AND reason_code = '{filters.get('reason_code')}'")
	
	if filters.get("recoverable"):
		conditions.append("AND recoverable = 1")
	
	return " ".join(conditions)


def get_chart_data(data):
	"""Get chart data for scrap by reason code"""
	reason_summary = {}
	
	for row in data:
		reason = row.get("reason_code", "Unknown")
		weight = flt(row.get("weight_kg", 0))
		
		if reason in reason_summary:
			reason_summary[reason] += weight
		else:
			reason_summary[reason] = weight
	
	return {
		"data": {
			"labels": list(reason_summary.keys()),
			"datasets": [
				{
					"name": "Scrap Weight (kg)",
					"values": list(reason_summary.values())
				}
			]
		},
		"type": "pie",
		"height": 300
	}


def get_report_summary(data):
	"""Get summary statistics for scrap"""
	total_weight = sum(flt(row.get("weight_kg", 0)) for row in data)
	total_loss = sum(flt(row.get("net_loss", 0)) for row in data)
	recoverable_count = sum(1 for row in data if row.get("recoverable"))
	
	return [
		{
			"value": total_weight,
			"label": "Total Scrap Weight (kg)",
			"datatype": "Float",
			"indicator": "Red"
		},
		{
			"value": total_loss,
			"label": "Total Net Loss",
			"datatype": "Currency",
			"indicator": "Red"
		},
		{
			"value": recoverable_count,
			"label": "Recoverable Items",
			"datatype": "Int",
			"indicator": "Green"
		},
		{
			"value": len(data),
			"label": "Total Scrap Records",
			"datatype": "Int",
			"indicator": "Blue"
		}
	]
