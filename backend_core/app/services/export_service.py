"""
Export service — generates Excel reports as BytesIO objects.

Extracted from tracking_api.py to keep routers thin.
"""

from io import BytesIO
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from .. import models


class ExportService:
    """Stateless service for Excel report generation."""

    @staticmethod
    def _items_to_bytesio(rows: List[dict], sheet_name: str) -> BytesIO:
        """Convert a list of row dicts into an Excel BytesIO."""
        df = pd.DataFrame(rows)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output

    @staticmethod
    def _query_completed_items(db: Session, *, archived: bool = False):
        """Return completed production items joined with non-deleted customers."""
        return (
            db.query(models.ProductionItem)
            .join(models.Customer)
            .filter(
                models.Customer.is_deleted == False,
                models.ProductionItem.is_completed == True,
                models.ProductionItem.is_archived == archived,
            )
        )

    @classmethod
    def export_dispatch_excel(cls, db: Session) -> BytesIO:
        """Dispatch report — completed, non-archived items."""
        items = cls._query_completed_items(db, archived=False).all()
        rows = [
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Stage": "Dispatch",
                "Completed At": it.stage_updated_at,
            }
            for it in items
        ]
        return cls._items_to_bytesio(rows, "Dispatch Report")

    @classmethod
    def export_completed_excel(cls, db: Session) -> BytesIO:
        """Completed jobs — non-archived."""
        items = (
            cls._query_completed_items(db, archived=False).order_by(models.ProductionItem.stage_updated_at.desc()).all()
        )
        rows = [
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Completed At": it.stage_updated_at,
            }
            for it in items
        ]
        return cls._items_to_bytesio(rows, "Completed Jobs")

    @classmethod
    def export_archived_excel(cls, db: Session) -> BytesIO:
        """Archived jobs."""
        items = (
            cls._query_completed_items(db, archived=True).order_by(models.ProductionItem.stage_updated_at.desc()).all()
        )
        rows = [
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Archived At": it.stage_updated_at,
            }
            for it in items
        ]
        return cls._items_to_bytesio(rows, "Archived Jobs")

    @classmethod
    def export_company_report(cls, db: Session) -> BytesIO:
        """Company-wise report — completed, non-archived, ordered by company."""
        items = (
            cls._query_completed_items(db, archived=False)
            .order_by(models.Customer.name, models.ProductionItem.stage_updated_at)
            .all()
        )
        rows = [
            {
                "Customer": it.customer.name if it.customer else "",
                "Item Code": it.item_code,
                "Item Name": it.item_name,
                "Section": it.section,
                "Quantity": it.quantity,
                "Completed At": it.stage_updated_at,
            }
            for it in items
        ]
        return cls._items_to_bytesio(rows, "Company Report")
