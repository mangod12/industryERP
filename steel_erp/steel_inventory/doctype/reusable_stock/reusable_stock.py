# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now


class ReusableStock(Document):
	def validate(self):
		"""Validate the document before save"""
		self.last_modified = now()
		self.validate_available_weight()

	def validate_available_weight(self):
		"""Ensure available weight is not negative"""
		if flt(self.available_weight) < 0:
			frappe.throw("Available weight cannot be negative")
		
		if flt(self.used_weight) > flt(self.available_weight):
			frappe.throw("Used weight cannot exceed available weight")

	@frappe.whitelist()
	def allocate_to_production(self, production_order, quantity):
		"""Allocate this reusable stock to a production order"""
		if self.is_allocated:
			frappe.throw("This reusable stock is already allocated")
		
		if flt(quantity) > flt(self.available_weight):
			frappe.throw("Requested quantity exceeds available weight")
		
		self.is_allocated = 1
		self.allocated_to = production_order
		self.used_weight = quantity
		self.available_weight = flt(self.available_weight) - flt(quantity)
		self.save()
		
		frappe.msgprint(f"Allocated {quantity} kg to {production_order}")

	@frappe.whitelist()
	def consume_stock(self, quantity):
		"""Consume reusable stock"""
		if flt(quantity) > flt(self.available_weight):
			frappe.throw("Requested quantity exceeds available weight")
		
		self.used_weight = flt(self.used_weight) + flt(quantity)
		self.available_weight = flt(self.available_weight) - flt(quantity)
		self.usage_date = frappe.utils.today()
		self.save()
		
		frappe.msgprint(f"Consumed {quantity} kg from reusable stock")

@frappe.whitelist()
def search_reusable_stock(material_item=None, min_weight=None, quality_grade=None):
	"""Search for available reusable stock matching criteria"""
	filters = {"is_allocated": 0}
	
	if material_item:
		filters["material_item"] = material_item
	
	if quality_grade:
		filters["quality_grade"] = quality_grade
	
	stocks = frappe.get_all(
		"Reusable Stock",
		filters=filters,
		fields=["name", "material_item", "item_name", "available_weight", 
		        "dimensions", "quality_grade", "warehouse", "heat_number"],
		order_by="available_weight desc"
	)
	
	if min_weight:
		stocks = [s for s in stocks if flt(s.available_weight) >= flt(min_weight)]
	
	return stocks
