# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ScrapRecord(Document):
	def validate(self):
		"""Validate the document before save"""
		self.calculate_financial_impact()

	def calculate_financial_impact(self):
		"""Calculate estimated loss value and net loss"""
		if self.material_item and self.weight_kg:
			# Get valuation rate from item
			valuation_rate = frappe.db.get_value(
				"Item",
				self.material_item,
				"valuation_rate"
			) or 0
			
			self.estimated_loss_value = flt(self.weight_kg) * flt(valuation_rate)
			self.net_loss_value = flt(self.estimated_loss_value) - flt(self.recovery_value)

	def on_submit(self):
		"""Create stock entry for scrap when submitted"""
		self.create_scrap_stock_entry()

	def create_scrap_stock_entry(self):
		"""Create Stock Entry for scrap material"""
		if self.recoverable:
			# If recoverable, move to reusable stock
			self.create_reusable_stock_record()
		else:
			# Create scrap stock entry
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.stock_entry_type = "Material Issue"
			stock_entry.company = frappe.defaults.get_defaults().get("company")
			stock_entry.posting_date = self.posting_date
			stock_entry.custom_scrap_record = self.name
			
			stock_entry.append("items", {
				"item_code": self.material_item,
				"qty": self.weight_kg,
				"uom": self.uom or "Kg",
				"s_warehouse": self.source_warehouse,
				"batch_no": self.batch_no if self.batch_no else None
			})
			
			stock_entry.insert()
			stock_entry.submit()

	def create_reusable_stock_record(self):
		"""Create Reusable Stock record for recoverable scrap"""
		reusable_stock = frappe.new_doc("Reusable Stock")
		reusable_stock.material_item = self.material_item
		reusable_stock.available_weight = self.weight_kg
		reusable_stock.quality_grade = "Scrap - Recoverable"
		reusable_stock.source_scrap_record = self.name
		reusable_stock.source_production_order = self.source_production_order
		reusable_stock.batch_no = self.batch_no
		reusable_stock.remarks = f"Recovered from scrap: {self.reason_code}"
		
		reusable_stock.insert()
		frappe.msgprint(f"Created Reusable Stock: {reusable_stock.name}")
