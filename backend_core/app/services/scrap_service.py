"""
ScrapService — Business logic for scrap and reusable stock management.
Extracted from scrap.py for separation of concerns.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)

SCRAP_LOSS_RATE_PER_KG = 50  # INR per kg for loss calculation


class ScrapService:
    """Business logic for scrap operations."""

    @staticmethod
    def return_to_inventory(
        db: Session,
        scrap_record_id: int,
        user_id: int,
    ) -> models.ScrapRecord:
        """
        Return scrap material back to inventory.
        Creates a negative MaterialUsage for audit trail.
        """
        record = db.query(models.ScrapRecord).filter(
            models.ScrapRecord.id == scrap_record_id
        ).first()

        if not record:
            raise ValueError(f"Scrap record {scrap_record_id} not found")

        if record.status != "pending":
            raise ValueError(f"Can only return pending scrap (current: {record.status})")

        # Find matching inventory item (lock row to prevent concurrent modification)
        inv = db.query(models.Inventory).filter(
            models.Inventory.name.ilike(f"%{record.material_name}%")
        ).with_for_update().first()

        if not inv:
            raise ValueError(
                f"No matching inventory item found for '{record.material_name}'. "
                "Cannot return to inventory."
            )

        # Return material (decrease used, effectively increasing available)
        new_used = (inv.used or 0) - record.weight_kg
        if new_used < 0:
            logger.warning(
                "Return of %.2f kg for '%s' exceeds used amount (%.2f kg). "
                "Clamping used to 0.",
                record.weight_kg, record.material_name, inv.used or 0,
            )
            new_used = 0
        inv.used = new_used
        db.add(inv)

        # Audit trail
        usage = models.MaterialUsage(
            customer_id=record.source_customer_id,
            production_item_id=record.source_item_id,
            name=record.material_name,
            qty=-record.weight_kg,  # Negative = return
            unit="kg",
            by=f"Returned from scrap (record #{record.id}, user: {user_id})",
            applied=True,
        )
        db.add(usage)

        record.status = "returned_to_inventory"
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            "Returned scrap record %s to inventory: %s %.2f kg",
            record.id, record.material_name, record.weight_kg,
        )
        return record

    @staticmethod
    def move_to_reusable(
        db: Session,
        scrap_record_id: int,
        quality_grade: str,
        user_id: int,
    ) -> models.ReusableStock:
        """Move a scrap record to reusable stock."""
        record = db.query(models.ScrapRecord).filter(
            models.ScrapRecord.id == scrap_record_id
        ).first()

        if not record:
            raise ValueError(f"Scrap record {scrap_record_id} not found")

        if record.status != "pending":
            raise ValueError(f"Can only move pending scrap (current: {record.status})")

        reusable = models.ReusableStock(
            material_name=record.material_name,
            weight_kg=record.weight_kg,
            length_mm=record.length_mm,
            width_mm=record.width_mm,
            quantity=record.quantity,
            dimensions=record.dimensions or f"{record.material_name}",
            source_item_id=record.source_item_id,
            source_customer_id=record.source_customer_id,
            quality_grade=quality_grade,
            notes=f"From scrap record #{record.id}",
            is_available=True,
            created_by=user_id,
        )
        db.add(reusable)

        record.status = "recycled"
        db.add(record)
        db.commit()
        db.refresh(reusable)
        return reusable

    @staticmethod
    def get_analytics(db: Session, days: int = 30) -> dict:
        """Get scrap analytics summary."""
        cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)

        records = db.query(models.ScrapRecord).filter(
            models.ScrapRecord.created_at >= cutoff
        ).all()

        total_weight = sum(r.weight_kg * r.quantity for r in records)
        total_records = len(records)

        # Group by reason code
        by_reason = {}
        for r in records:
            code = r.reason_code
            if code not in by_reason:
                by_reason[code] = {"count": 0, "weight_kg": 0}
            by_reason[code]["count"] += 1
            by_reason[code]["weight_kg"] += r.weight_kg * r.quantity

        # Group by material
        by_material = {}
        for r in records:
            mat = r.material_name
            if mat not in by_material:
                by_material[mat] = {"count": 0, "weight_kg": 0}
            by_material[mat]["count"] += 1
            by_material[mat]["weight_kg"] += r.weight_kg * r.quantity

        return {
            "period_days": days,
            "total_records": total_records,
            "total_weight_kg": round(total_weight, 2),
            "estimated_loss_inr": round(total_weight * SCRAP_LOSS_RATE_PER_KG, 2),
            "by_reason": by_reason,
            "by_material": by_material,
            "status_counts": {
                "pending": sum(1 for r in records if r.status == "pending"),
                "returned": sum(1 for r in records if r.status == "returned_to_inventory"),
                "recycled": sum(1 for r in records if r.status == "recycled"),
                "disposed": sum(1 for r in records if r.status == "disposed"),
                "sold": sum(1 for r in records if r.status == "sold"),
            },
        }
