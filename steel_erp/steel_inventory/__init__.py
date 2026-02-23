"""Steel Inventory Module"""

import frappe
from frappe.utils import flt


def create_batch_from_pr(doc, method):
	"""Create batches with heat numbers from Purchase Receipt"""
	for item in doc.items:
		if item.item_code and not item.batch_no:
			# Check if item has batch tracking
			has_batch = frappe.db.get_value("Item", item.item_code, "has_batch_no")
			if has_batch:
				# Create batch with heat number from custom fields
				batch = frappe.new_doc("Batch")
				batch.item = item.item_code
				batch.batch_id = f"{item.item_code}-{doc.name}"
				
				# Set custom fields if available
				if hasattr(doc, 'custom_vehicle_number'):
					batch.custom_heat_number = doc.custom_vehicle_number or ""
				
				batch.insert()
				item.batch_no = batch.name


def validate_dispatch_weights(doc, method):
	"""Validate weighbridge weights for Delivery Note"""
	if hasattr(doc, 'custom_gross_weight') and hasattr(doc, 'custom_tare_weight'):
		gross = flt(doc.custom_gross_weight)
		tare = flt(doc.custom_tare_weight)
		
		if gross > 0 and tare > 0:
			doc.custom_net_weight = gross - tare
			
			# Validate net weight matches item quantities
			total_item_weight = sum(flt(item.qty) for item in doc.items)
			net_weight = doc.custom_net_weight
			
			# Allow 2% variance
			variance = abs(total_item_weight - net_weight) / total_item_weight * 100 if total_item_weight > 0 else 0
			
			if variance > 2:
				frappe.msgprint(
					f"Warning: Weighbridge net weight ({net_weight} kg) differs from "
					f"item total ({total_item_weight} kg) by {variance:.1f}%",
					alert=True
				)
