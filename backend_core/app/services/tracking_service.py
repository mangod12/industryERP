"""
TrackingService — Stage transition logic and validation.
Extracted from tracking.py for separation of concerns.

Contains business logic for:
  - Stage validation and ordering
  - Stage history management
  - Dashboard summary computation
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)

STAGE_ORDER = ["fabrication", "painting", "dispatch"]


class TrackingService:
    """Business logic for production stage tracking."""

    @staticmethod
    def validate_stage_transition(
        db: Session,
        item: models.ProductionItem,
        target_stage: str,
    ) -> None:
        """
        Validate that a stage transition is allowed.
        Raises ValueError if not.
        """
        if target_stage not in STAGE_ORDER:
            raise ValueError(f"Invalid stage: {target_stage}")

        idx = STAGE_ORDER.index(target_stage)

        # Check previous stage is completed
        if idx > 0:
            prev_stage = STAGE_ORDER[idx - 1]
            prev_row = (
                db.query(models.StageTracking)
                .filter(
                    models.StageTracking.production_item_id == item.id,
                    models.StageTracking.stage == prev_stage,
                    models.StageTracking.status == "completed",
                )
                .first()
            )
            if not prev_row:
                raise ValueError(
                    f"Previous stage '{prev_stage}' must be completed "
                    f"before starting '{target_stage}'"
                )

        # Check no other stage in progress
        in_progress = (
            db.query(models.StageTracking)
            .filter(
                models.StageTracking.production_item_id == item.id,
                models.StageTracking.status == "in_progress",
            )
            .first()
        )
        if in_progress:
            raise ValueError("Another stage is already in progress")

    @staticmethod
    def record_stage_history(
        db: Session,
        item_id: int,
        from_stage: str,
        to_stage: str,
        user_id: int,
        remarks: Optional[str] = None,
    ) -> models.TrackingStageHistory:
        """Record a stage change in the history table."""
        history = models.TrackingStageHistory(
            material_id=item_id,
            from_stage=from_stage,
            to_stage=to_stage,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            remarks=remarks,
        )
        db.add(history)
        return history

    @staticmethod
    def compute_customer_stage(
        db: Session, customer: models.Customer
    ) -> str:
        """
        Compute a customer-level stage from its production items.
        Returns the highest in-progress or completed stage.
        """
        all_stage_rows = []
        for item in customer.production_items:
            rows = (
                db.query(models.StageTracking)
                .filter(models.StageTracking.production_item_id == item.id)
                .all()
            )
            all_stage_rows.extend(rows)

        in_progress = [r for r in all_stage_rows if r.status == "in_progress"]
        if in_progress:
            return in_progress[0].stage.capitalize()

        completed = [r for r in all_stage_rows if r.status == "completed"]
        if not completed:
            return "Pending"

        completed_stages = {r.stage for r in completed}
        for s in reversed(STAGE_ORDER):
            if s in completed_stages:
                return s.capitalize()

        return "Pending"

    @staticmethod
    def get_inventory_stats(db: Session) -> dict:
        """Get inventory summary statistics."""
        items = db.query(models.Inventory).all()
        total = len(items)
        low_stock = sum(
            1
            for item in items
            if item.total > 0 and (item.total - item.used) / item.total < 0.15
        )
        total_value = sum((item.total - item.used) for item in items)

        return {
            "total_materials": total,
            "total_value": total_value,
            "low_stock_count": low_stock,
        }
