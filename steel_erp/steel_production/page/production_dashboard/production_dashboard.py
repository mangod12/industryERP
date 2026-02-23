# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_dashboard_data():
	"""Get comprehensive dashboard data for production overview"""
	
	# Production Order Summary
	total_orders = frappe.db.count("Steel Production Order")
	in_progress = frappe.db.count("Steel Production Order", {"status": "In Progress"})
	completed = frappe.db.count("Steel Production Order", {"status": "Completed"})
	on_hold = frappe.db.count("Steel Production Order", {"status": "On Hold"})
	
	# Stage Summary
	stage_summary = get_stage_summary()
	
	# Inventory Summary
	inventory_summary = get_inventory_summary()
	
	# Recent Activities
	recent_activities = get_recent_activities()
	
	return {
		"total_orders": total_orders,
		"in_progress": in_progress,
		"completed": completed,
		"on_hold": on_hold,
		"stage_summary": stage_summary,
		"inventory_summary": inventory_summary,
		"recent_activities": recent_activities
	}


def get_stage_summary():
	"""Get count of items in each production stage"""
	stages = ["Fabrication", "Painting", "Dispatch", "Completed"]
	summary = []
	
	for stage_name in stages:
		# Count by stage status
		stage_data = frappe.db.sql("""
			SELECT 
				ps.status,
				COUNT(*) as count
			FROM `tabProduction Stage` ps
			INNER JOIN `tabSteel Production Order` spo ON ps.parent = spo.name
			WHERE ps.stage_name = %s
			AND spo.docstatus = 1
			GROUP BY ps.status
		""", stage_name, as_dict=True)
		
		stage_counts = {
			"stage_name": stage_name,
			"not_started": 0,
			"in_progress": 0,
			"completed": 0
		}
		
		for data in stage_data:
			if data.status == "Not Started":
				stage_counts["not_started"] = data.count
			elif data.status == "In Progress":
				stage_counts["in_progress"] = data.count
			elif data.status == "Completed":
				stage_counts["completed"] = data.count
		
		summary.append(stage_counts)
	
	return summary


def get_inventory_summary():
	"""Get inventory summary with utilization"""
	inventory_items = frappe.db.sql("""
		SELECT 
			i.name,
			i.item_name,
			i.custom_profile_section,
			COALESCE(SUM(b.actual_qty), 0) as available_qty
		FROM `tabItem` i
		LEFT JOIN `tabBin` b ON i.name = b.item_code
		WHERE i.custom_profile_section IS NOT NULL
		AND i.custom_profile_section != ''
		GROUP BY i.name
		ORDER BY available_qty DESC
		LIMIT 10
	""", as_dict=True)
	
	summary = []
	for item in inventory_items:
		# Calculate consumed qty from stock ledger
		consumed = frappe.db.sql("""
			SELECT SUM(actual_qty) as consumed
			FROM `tabStock Ledger Entry`
			WHERE item_code = %s
			AND actual_qty < 0
		""", item.name)
		
		consumed_qty = abs(flt(consumed[0][0])) if consumed and consumed[0] else 0
		available_qty = flt(item.available_qty)
		total_purchased = available_qty + consumed_qty
		
		utilization = (consumed_qty / total_purchased * 100) if total_purchased > 0 else 0
		
		# Determine status
		if utilization > 85:
			status = "Critical"
		elif utilization > 70:
			status = "Low Stock"
		else:
			status = "OK"
		
		summary.append({
			"item_name": item.item_name or item.name,
			"profile": item.custom_profile_section,
			"available": available_qty,
			"consumed": consumed_qty,
			"utilization": utilization,
			"status": status
		})
	
	return summary


def get_recent_activities():
	"""Get recent production activities"""
	activities = frappe.db.sql("""
		SELECT 
			name,
			customer,
			status,
			current_stage,
			modified
		FROM `tabSteel Production Order`
		WHERE docstatus = 1
		ORDER BY modified DESC
		LIMIT 10
	""", as_dict=True)
	
	return activities
