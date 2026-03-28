# Copyright (c) 2026, KumarBrothers Steel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, flt


class SteelProductionOrder(Document):
	def validate(self):
		"""Validate the document before save"""
		self.calculate_total_weight()
		self.set_stage_order()
		self.update_status()
		self.calculate_completion()

	def calculate_total_weight(self):
		"""Calculate total weight from quantity and weight per unit"""
		if self.quantity and self.weight_per_unit:
			self.total_weight = flt(self.quantity) * flt(self.weight_per_unit)

	def set_stage_order(self):
		"""Set the sequential order for production stages"""
		stage_mapping = {
			"Fabrication": 1,
			"Painting": 2,
			"Dispatch": 3,
			"Completed": 4
		}
		
		for stage in self.production_stages:
			stage.stage_order = stage_mapping.get(stage.stage_name, 0)

	def update_status(self):
		"""Update overall status based on production stages"""
		if not self.production_stages:
			self.status = "Draft"
			return

		all_completed = all(stage.status == "Completed" for stage in self.production_stages)
		any_in_progress = any(stage.status == "In Progress" for stage in self.production_stages)
		any_on_hold = any(stage.status == "On Hold" for stage in self.production_stages)

		if all_completed:
			self.status = "Completed"
		elif any_on_hold:
			self.status = "On Hold"
		elif any_in_progress:
			self.status = "In Progress"
		else:
			self.status = "Draft"

		# Set current stage
		for stage in sorted(self.production_stages, key=lambda x: x.stage_order):
			if stage.status != "Completed":
				self.current_stage = stage.stage_name
				break
		else:
			self.current_stage = "Completed"

	def calculate_completion(self):
		"""Calculate overall completion percentage"""
		if not self.production_stages:
			self.overall_completion = 0
			return

		completed_stages = sum(1 for stage in self.production_stages if stage.status == "Completed")
		total_stages = len(self.production_stages)
		self.overall_completion = (completed_stages / total_stages) * 100 if total_stages > 0 else 0

	def on_submit(self):
		"""Initialize production stages if not exists"""
		if not self.production_stages:
			self.add_default_stages()

	def add_default_stages(self):
		"""Add default production stages: Fabrication, Painting, Dispatch, Completed"""
		default_stages = ["Fabrication", "Painting", "Dispatch", "Completed"]
		
		for idx, stage_name in enumerate(default_stages, start=1):
			self.append("production_stages", {
				"stage_name": stage_name,
				"stage_order": idx,
				"status": "Not Started"
			})

	@frappe.whitelist()
	def start_stage(self, stage_name):
		"""Start a production stage"""
		for stage in self.production_stages:
			if stage.stage_name == stage_name:
				if stage.status == "Completed":
					frappe.throw(f"Stage {stage_name} is already completed")
				
				stage.status = "In Progress"
				stage.started_at = now()
				stage.operator = frappe.session.user
				break
		
		self.save()
		frappe.msgprint(f"Started stage: {stage_name}")

	@frappe.whitelist()
	def complete_stage(self, stage_name):
		"""Complete a production stage and trigger material deduction for Fabrication"""
		for stage in self.production_stages:
			if stage.stage_name == stage_name:
				if stage.status != "In Progress":
					frappe.throw(f"Stage {stage_name} must be 'In Progress' before completion")
				
				stage.status = "Completed"
				stage.completed_at = now()
				
				# Trigger material deduction for Fabrication stage
				if stage_name == "Fabrication" and not stage.material_deducted:
					self.deduct_materials()
					stage.material_deducted = 1
				
				break
		
		self.save()
		frappe.msgprint(f"Completed stage: {stage_name}")

	def deduct_materials(self):
		"""Deduct materials from inventory when Fabrication is completed"""
		from steel_erp.steel_production import create_material_stock_entry
		
		if not self.material_requirements:
			# Auto-create material requirement from profile/section
			if self.profile_section and self.total_weight:
				self.create_material_requirement_from_profile()
		
		# Create stock entry for material consumption
		try:
			stock_entry = create_material_stock_entry(self)
			frappe.msgprint(f"Materials deducted successfully. Stock Entry: {stock_entry}")
		except Exception as e:
			frappe.log_error(f"Material deduction failed: {str(e)}", "Steel Production Order")
			frappe.throw(f"Failed to deduct materials: {str(e)}")

	def create_material_requirement_from_profile(self):
		"""Auto-create material requirement based on profile/section"""
		# Search for matching item by profile_section
		items = frappe.get_all(
			"Item",
			filters={"custom_profile_section": self.profile_section},
			fields=["name"]
		)
		
		if items:
			self.append("material_requirements", {
				"item": items[0].name,
				"required_qty": self.total_weight,
				"uom": "Kg"
			})
