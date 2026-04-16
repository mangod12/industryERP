from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any
from datetime import datetime
from .. import models

STAGE_FLOW = {
    "fabrication": "painting",
    "painting": "dispatch",
    "dispatch": "completed",
    "completed": None
}

class TrackingService:
    
    @staticmethod
    def _capitalize(s: Optional[str]):
        return s.capitalize() if s else s

    @staticmethod
    def _get_or_create_stage(db: Session, item_id: int, stage: str, user_id: int):
        """Return existing StageTracking row for (item_id, stage) or create an in_progress one.
        Best-effort: adds the row to the session but does not commit.
        """
        row = db.query(models.StageTracking).filter(
            models.StageTracking.production_item_id == item_id,
            models.StageTracking.stage == stage
        ).first()

        if not row:
            row = models.StageTracking(
                production_item_id=item_id,
                stage=stage,
                status="in_progress",
                started_at=datetime.utcnow(),
                updated_by=user_id
            )
            db.add(row)
        return row

    @staticmethod
    def _deduct_materials_for_fabrication(item: models.ProductionItem, db: Session, user_id: int) -> dict:
        """
        Automatically deduct raw materials from inventory when fabrication is completed.
        This only happens ONCE per item (tracked via fabrication_deducted flag).
        
        Returns:
            dict with deduction details: {success: bool, deducted: [], skipped_reason: str}
        """
        import json
        result: Dict[str, Any] = {"success": False, "deducted": [], "skipped_reason": None, "warnings": []}
        
        if item.fabrication_deducted:
            result["skipped_reason"] = "Already deducted"
            return result
        
        # Parse material requirements from JSON (set during Excel import)
        material_reqs = []
        if item.material_requirements:
            try:
                material_reqs = json.loads(item.material_requirements)
            except json.JSONDecodeError:
                result["warnings"].append("Invalid material_requirements JSON")
        
        # If no specific material requirements, try to auto-calculate based on item properties
        # Using robust matching logic from ProductionService (Section -> ItemCode -> Fuzzy)
        if not material_reqs and (item.section or item.item_code):
            from .production_service import ProductionService
            
            inv_item = ProductionService._find_inventory_match(
                profile=item.section, 
                db=db, 
                item_code=item.item_code
            )
            
            if inv_item:
                # Calculate qty based on weight and quantity
                qty = (item.quantity or 1) * (item.weight_per_unit or 0)
                if qty > 0:
                    material_reqs = [{"material_id": inv_item.id, "qty": qty, "inventory_name": inv_item.name}]
            else:
                result["warnings"].append(f"No inventory match for section '{item.section}' or code '{item.item_code}'")
        
        if not material_reqs:
            result["skipped_reason"] = "No material requirements set and no auto-match found"
            # Create notification for admin
            notification = models.Notification(
                role="Boss",
                message=f"⚠️ Item '{item.item_name}' (Code: {item.item_code}) completed Fabrication but has no material link. No auto-deduction performed.",
                level="warning",
                category="low_inventory"
            )
            db.add(notification)
            # Still mark as deducted to prevent retry
            item.fabrication_deducted = True
            db.add(item)
            return result
        
        # Deduct materials from inventory
        for req in material_reqs:
            material_id = req.get("material_id")
            qty = req.get("qty", 0)
            
            if material_id and qty > 0:
                inv_item = db.query(models.Inventory).filter(models.Inventory.id == material_id).first()
                if inv_item:
                    # Check if enough stock
                    available = (inv_item.total or 0) - (inv_item.used or 0)
                    if available < qty:
                        result["warnings"].append(f"Low stock warning: {inv_item.name} needs {qty:.2f}, only {available:.2f} available")
                        # Create low stock notification
                        notification = models.Notification(
                            role="Boss",
                            message=f"⚠️ Low Stock Alert: '{inv_item.name}' - needed {qty:.2f} for item '{item.item_name}', only {available:.2f} available",
                            level="warning",
                            category="low_inventory"
                        )
                        db.add(notification)
                    
                    # Perform deduction (even if going negative - admin can adjust)
                    inv_item.used = (inv_item.used or 0) + qty
                    db.add(inv_item)
                    
                    # Log the material usage
                    usage = models.MaterialUsage(
                        customer_id=item.customer_id,
                        production_item_id=item.id,
                        name=inv_item.name,
                        qty=qty,
                        unit=inv_item.unit,
                        by=f"Auto-deducted on fabrication completion (user: {user_id})"
                    )
                    db.add(usage)
                    
                    result["deducted"].append({
                        "material": inv_item.name,
                        "qty": qty,
                        "unit": inv_item.unit
                    })
        
        # Mark as deducted
        item.fabrication_deducted = True
        item.material_deducted = True  # Also set the alias flag
        db.add(item)
        
        result["success"] = len(result["deducted"]) > 0
        return result

    @staticmethod
    def update_order_status_if_completed(db: Session, customer_id: int):
        incomplete_items = (
            db.query(models.ProductionItem)
            .filter(
                models.ProductionItem.customer_id == customer_id,
                models.ProductionItem.is_completed == False
            )
            .count()
        )

        if incomplete_items == 0:
            customer = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
            if customer:
                customer.order_status = "COMPLETED"
                db.add(customer)
                db.commit()

    @classmethod
    def toggle_checklist(cls, db: Session, item_id: int, is_checked: bool, user_id: int) -> bool:
        """
        updates the is_checked status of the current stage of an item
        """
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise ValueError("Production item not found")

        cur_stage = (item.current_stage or "fabrication").lower()
        
        st = (
            db.query(models.StageTracking)
            .filter_by(production_item_id=item.id, stage=cur_stage)
            .first()
        )

        if not st:
            st = models.StageTracking(
                production_item_id=item.id,
                stage=cur_stage,
                status="in_progress"
            )
            db.add(st)

        st.is_checked = is_checked
        # db.commit() REMOVED - handled by API layer
        return True

    @classmethod
    def advance_stage(cls, db: Session, item_id: int, target_stage: str, user_id: int, move_quantity: Optional[float] = None) -> Dict[str, Any]:
        """
        Advances item to the target stage if valid.
        Supports partial moves by splitting the item first.
        """
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise ValueError("Production item not found")

        # Handle Partial Move
        active_item = item
        if move_quantity is not None and move_quantity > 0 and move_quantity < item.quantity:
            split_result = cls.split_item(db, item_id, move_quantity)
            active_item = db.query(models.ProductionItem).filter_by(id=split_result["new_item_id"]).first()

        cur_stage = (active_item.current_stage or "fabrication").lower()
        requested = target_stage.lower()
        next_stage = STAGE_FLOW.get(cur_stage)

        if requested != next_stage:
             raise ValueError(f"Stage must advance to '{next_stage}' (requested '{requested}' from '{cur_stage}')")

        st = (
            db.query(models.StageTracking)
            .filter_by(production_item_id=active_item.id, stage=cur_stage)
            .first()
        )

        if not st or not st.is_checked:
            raise ValueError("Checklist must be completed first")

        now = datetime.utcnow()

        # COMPLETE CURRENT STAGE
        st.status = "completed"
        st.completed_at = now
        st.updated_by = user_id
        db.add(st)

        # TRIGGER MATERIAL DEDUCTION IF COMPLETING 'FABRICATION'
        if cur_stage == "fabrication" and requested != "fabrication":
             cls._deduct_materials_for_fabrication(active_item, db, user_id)

        # MOVE TO NEXT STAGE
        active_item.current_stage = requested
        active_item.stage_updated_at = now
        active_item.stage_updated_by = user_id
        db.add(active_item)

        # CREATE / START NEXT STAGE ROW
        if requested != "completed":
            next_stage_row = cls._get_or_create_stage(
                db=db,
                item_id=active_item.id,
                stage=requested,
                user_id=user_id
            )
            next_stage_row.status = "in_progress"
            next_stage_row.started_at = now
            db.add(next_stage_row)

        # FINAL COMPLETION LOGIC
        if requested == "completed":
            active_item.is_completed = True
            active_item.current_stage = "completed"

        # db.commit() REMOVED for atomicity - handled by caller or top-level service method

        if requested == "completed":
            try:
                cls.update_order_status_if_completed(db, active_item.customer_id)
            except Exception:
                pass
        
        return {"status": "updated", "current_stage": active_item.current_stage, "item_id": active_item.id}

    @classmethod
    def split_item(cls, db: Session, item_id: int, move_quantity: float) -> Dict[str, Any]:
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise ValueError("Production item not found")

        if item.is_completed:
            raise ValueError("Cannot split a completed item")

        if move_quantity <= 0:
            raise ValueError("Quantity must be positive")

        if move_quantity >= item.quantity:
            raise ValueError("Move quantity must be less than existing quantity")

        original_qty = item.quantity
        
        # Reduce quantity of original item
        item.quantity = (item.quantity or 0) - move_quantity
        
        # Handle Material Requirements Split
        new_item_reqs = item.material_requirements
        
        if item.material_requirements:
            try:
                reqs = json.loads(item.material_requirements)
                new_reqs_for_child = []
                new_reqs_for_original = []
                
                for r in reqs:
                    total_stored = float(r.get("qty", 0))
                    if original_qty > 0:
                        per_unit = total_stored / original_qty
                        child_qty_share = per_unit * move_quantity
                        
                        r_child = r.copy()
                        r_child["qty"] = child_qty_share
                        new_reqs_for_child.append(r_child)
                        
                        r["qty"] = total_stored - child_qty_share
                        new_reqs_for_original.append(r)
                    else:
                        new_reqs_for_child.append(r)
                        new_reqs_for_original.append(r)
                
                new_item_reqs = json.dumps(new_reqs_for_child)
                item.material_requirements = json.dumps(new_reqs_for_original)
                
            except Exception:
                pass

        # Clone item for moved quantity
        new_item = models.ProductionItem(
            item_code=item.item_code, # Keep same code as per user request for Drawing No tracking
            item_name=item.item_name,
            section=item.section,
            quantity=move_quantity,
            unit=item.unit,
            weight_per_unit=item.weight_per_unit, # Ensure weight is preserved
            customer_id=item.customer_id,
            current_stage=item.current_stage,
            parent_item_id=item.id,
            material_requirements=new_item_reqs,
            # Inherit deduction flags to keep state consistent across segments
            fabrication_deducted=item.fabrication_deducted,
            material_deducted=item.material_deducted,
            notes=(item.notes or "") + f"\nSplit from item {item.id}",
        )

        db.add(new_item)
        db.add(item)
        db.flush() 

        # We need to clone the current stage status too
        cur_st_original = db.query(models.StageTracking).filter_by(
            production_item_id=item.id, 
            stage=item.current_stage.lower()
        ).first()

        if cur_st_original:
            new_st = models.StageTracking(
                production_item_id=new_item.id,
                stage=cur_st_original.stage,
                status=cur_st_original.status,
                is_checked=cur_st_original.is_checked, # Inherit checklist status for easier partial move
                started_at=cur_st_original.started_at,
                updated_by=cur_st_original.updated_by
            )
            db.add(new_st)

        # Initialize OTHER pending stages for the new item
        for s_name in ["fabrication", "painting", "dispatch"]:
            if s_name != item.current_stage.lower():
                db.add(models.StageTracking(
                    production_item_id=new_item.id,
                    stage=s_name,
                ))

        db.flush() # Ensure new item and stages are flushed to session
        # db.commit() REMOVED for atomicity
        db.refresh(new_item)

        return {
            "message": "Quantity split successfully",
            "original_item_id": item.id,
            "new_item_id": new_item.id,
            "remaining_quantity": item.quantity,
            "moved_quantity": move_quantity
        }

    @classmethod
    def archive_item(cls, db: Session, item_id: int) -> bool:
        item = db.query(models.ProductionItem).filter_by(id=item_id).first()
        if not item:
            raise ValueError("Item not found")

        if not item.is_completed:
            raise ValueError("Only completed items can be archived")

        if getattr(item, 'is_archived', False):
            raise ValueError("Item is already archived")

        item.is_archived = True
        db.add(item)
        db.commit()
        return True
