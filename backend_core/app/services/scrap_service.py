"""
Scrap and Reusable Stock Service
=================================
Business logic for scrap recording, reusable stock tracking, and loss analytics.
Extracted from scrap.py router to follow the service-layer pattern.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import pandas

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models

# TODO: Move to system_config table for runtime configurability
DEFAULT_SCRAP_RATE_PER_KG = 50

VALID_SCRAP_STATUSES = ["pending", "returned_to_inventory", "disposed", "recycled", "sold"]

VALID_REASON_CODES = ["cutting_waste", "defect", "damage", "overrun", "leftover"]

# Column aliases for CSV import normalization
CSV_COLUMN_MAPPING = {
    "material": "material_name",
    "name": "material_name",
    "item": "material_name",
    "profile": "material_name",
    "section": "material_name",
    "dimension": "dimensions",
    "size": "dimensions",
    "dims": "dimensions",
    "weight": "weight_kg",
    "wt": "weight_kg",
    "kg": "weight_kg",
    "qty": "quantity",
    "pcs": "quantity",
    "pieces": "quantity",
    "nos": "quantity",
    "reason": "reason_code",
    "type": "reason_code",
    "waste_type": "reason_code",
    "length": "length_mm",
    "len": "length_mm",
    "width": "width_mm",
}


class ScrapService:
    """Service class for scrap record operations."""

    @staticmethod
    def _normalize_import_dataframe(df: "pandas.DataFrame") -> tuple["pandas.DataFrame", List[str]]:
        normalized = df.copy()
        normalized.columns = [str(c).lower().strip().replace(" ", "_") for c in normalized.columns]

        for old_col, new_col in CSV_COLUMN_MAPPING.items():
            if old_col in normalized.columns and new_col not in normalized.columns:
                normalized.rename(columns={old_col: new_col}, inplace=True)

        required_cols = ["material_name", "weight_kg"]
        missing = [c for c in required_cols if c not in normalized.columns]
        return normalized, missing

    @staticmethod
    def preview_bulk_import_csv(df: "pandas.DataFrame") -> Dict[str, Any]:
        """
        Parse scrap upload rows without writing to the database.

        Returns the same grouping shape as the import path, plus validation
        details that let operators decide whether to confirm the import.
        """
        df, missing = ScrapService._normalize_import_dataframe(df)
        if missing:
            return {
                "ready_to_import": False,
                "missing_columns": missing,
                "columns": list(df.columns),
                "rows_count": int(len(df)),
                "records_count": 0,
                "grouped_items": [],
                "total_weight_kg": 0,
                "errors": [f"Missing columns: {missing}"],
            }

        grouped_items: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []
        records_count = 0
        total_weight = 0.0

        for index, row in df.iterrows():
            row_number = int(index) + 2
            material = str(row.get("material_name", "")).strip()
            if not material or material.lower() == "nan":
                continue

            try:
                weight = float(row.get("weight_kg", 0) or 0)
            except (TypeError, ValueError):
                errors.append(f"Row {row_number}: weight_kg must be numeric")
                continue
            if weight <= 0:
                errors.append(f"Row {row_number}: weight_kg must be greater than 0")
                continue

            try:
                quantity = int(row.get("quantity", 1) or 1)
            except (TypeError, ValueError):
                errors.append(f"Row {row_number}: quantity must be a number")
                continue
            if quantity <= 0:
                errors.append(f"Row {row_number}: quantity must be greater than 0")
                continue

            reason = str(row.get("reason_code", "leftover") or "leftover").strip()
            if reason not in VALID_REASON_CODES:
                errors.append(f"Row {row_number}: reason_code must be one of {', '.join(VALID_REASON_CODES)}")
                continue

            dimensions = str(row.get("dimensions", "") or "")
            group_key = f"{material}|{dimensions}"
            if group_key not in grouped_items:
                grouped_items[group_key] = {
                    "material_name": material,
                    "dimensions": dimensions,
                    "total_weight_kg": 0,
                    "total_quantity": 0,
                    "records": [],
                }

            grouped_items[group_key]["total_weight_kg"] += weight
            grouped_items[group_key]["total_quantity"] += quantity
            grouped_items[group_key]["records"].append(
                {"row": row_number, "weight_kg": weight, "quantity": quantity, "reason_code": reason}
            )
            records_count += 1
            total_weight += weight

        return {
            "ready_to_import": records_count > 0 and not errors,
            "missing_columns": [],
            "columns": list(df.columns),
            "rows_count": int(len(df)),
            "records_count": records_count,
            "grouped_items": list(grouped_items.values()),
            "total_weight_kg": round(total_weight, 3),
            "errors": errors,
        }

    @staticmethod
    def list_scrap_records(
        db: Session,
        *,
        status: Optional[str] = None,
        reason_code: Optional[str] = None,
        material_name: Optional[str] = None,
    ) -> List[models.ScrapRecord]:
        """List scrap records with optional filters."""
        query = db.query(models.ScrapRecord)

        if status:
            query = query.filter(models.ScrapRecord.status == status)
        if reason_code:
            query = query.filter(models.ScrapRecord.reason_code == reason_code)
        if material_name:
            query = query.filter(models.ScrapRecord.material_name.ilike(f"%{material_name}%"))

        return query.order_by(models.ScrapRecord.created_at.desc()).all()

    @staticmethod
    def create_scrap_record(
        db: Session,
        *,
        material_name: str,
        weight_kg: float,
        reason_code: str,
        user_id: int,
        length_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
        quantity: int = 1,
        source_item_id: Optional[int] = None,
        source_customer_id: Optional[int] = None,
        dimensions: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> models.ScrapRecord:
        """Create a new scrap record with validation."""
        if weight_kg <= 0:
            raise ValueError("Weight must be positive")

        record = models.ScrapRecord(
            material_name=material_name,
            weight_kg=weight_kg,
            length_mm=length_mm,
            width_mm=width_mm,
            quantity=quantity,
            reason_code=reason_code,
            source_item_id=source_item_id,
            source_customer_id=source_customer_id,
            dimensions=dimensions,
            notes=notes,
            status="pending",
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def update_scrap_status(
        db: Session,
        record_id: int,
        new_status: str,
        scrap_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update a scrap record's status."""
        record = db.query(models.ScrapRecord).filter(models.ScrapRecord.id == record_id).first()
        if not record:
            raise LookupError("Scrap record not found")

        if new_status not in VALID_SCRAP_STATUSES:
            raise ValueError(f"Status must be one of: {VALID_SCRAP_STATUSES}")

        record.status = new_status
        if scrap_value is not None:
            record.scrap_value = scrap_value

        db.commit()
        return {"message": "Status updated", "id": record_id, "status": new_status}

    @staticmethod
    def return_to_inventory(
        db: Session,
        record_id: int,
    ) -> Dict[str, Any]:
        """Return scrap back to main inventory (for reusable pieces)."""
        record = db.query(models.ScrapRecord).filter(models.ScrapRecord.id == record_id).first()
        if not record:
            raise LookupError("Scrap record not found")

        if record.status == "returned_to_inventory":
            raise ValueError("Already returned to inventory")

        # Find matching inventory item or create new
        inv = db.query(models.Inventory).filter(models.Inventory.name.ilike(f"%{record.material_name}%")).first()

        if inv:
            inv.total = (inv.total or 0) + record.weight_kg
        else:
            inv = models.Inventory(
                name=record.material_name,
                unit="kg",
                total=record.weight_kg,
                used=0,
                category="reusable",
                created_at=datetime.utcnow(),
            )
            db.add(inv)

        record.status = "returned_to_inventory"
        db.commit()

        return {
            "message": "Returned to inventory",
            "material": record.material_name,
            "weight_kg": record.weight_kg,
            "inventory_id": inv.id,
        }

    @staticmethod
    def move_to_reusable(
        db: Session,
        record_id: int,
        quality_grade: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """Move scrap to reusable stock (for offcuts that can be used later)."""
        record = db.query(models.ScrapRecord).filter(models.ScrapRecord.id == record_id).first()
        if not record:
            raise LookupError("Scrap record not found")

        reusable = models.ReusableStock(
            material_name=record.material_name,
            dimensions=record.dimensions or f"{record.length_mm}mm x {record.width_mm}mm",
            weight_kg=record.weight_kg,
            length_mm=record.length_mm,
            width_mm=record.width_mm,
            quantity=record.quantity,
            source_item_id=record.source_item_id,
            source_customer_id=record.source_customer_id,
            quality_grade=quality_grade,
            is_available=True,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        db.add(reusable)

        record.status = "returned_to_inventory"
        db.commit()
        db.refresh(reusable)

        return {
            "message": "Moved to reusable stock",
            "reusable_id": reusable.id,
            "material": record.material_name,
        }

    @staticmethod
    def delete_scrap_record(db: Session, record_id: int) -> Dict[str, Any]:
        """Delete a scrap record."""
        record = db.query(models.ScrapRecord).filter(models.ScrapRecord.id == record_id).first()
        if not record:
            raise LookupError("Scrap record not found")

        db.delete(record)
        db.commit()
        return {"message": "Scrap record deleted", "id": record_id}

    @staticmethod
    def bulk_import_csv(
        db: Session,
        df: "pandas.DataFrame",
        user_id: int,
        customer_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Import scrap records from a pre-parsed DataFrame.

        The caller (router) is responsible for file reading and encoding;
        this method handles column normalization, validation, and DB inserts.
        Returns grouped similar items for review.
        """
        df, missing = ScrapService._normalize_import_dataframe(df)
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        preview = ScrapService.preview_bulk_import_csv(df)
        if not preview["ready_to_import"]:
            raise ValueError("; ".join(preview.get("errors") or ["No valid scrap rows found"]))

        # Process and group similar items
        records_created: List[models.ScrapRecord] = []
        grouped_items: Dict[str, Dict[str, Any]] = {}

        for _, row in df.iterrows():
            material = str(row.get("material_name", "")).strip()
            if not material or material == "nan":
                continue

            weight = float(row.get("weight_kg", 0) or 0)
            quantity = int(row.get("quantity", 1) or 1)
            dimensions = str(row.get("dimensions", "") or "")
            reason = str(row.get("reason_code", "leftover") or "leftover")
            length_mm = float(row.get("length_mm", 0) or 0) if "length_mm" in df.columns else None
            width_mm = float(row.get("width_mm", 0) or 0) if "width_mm" in df.columns else None

            record = models.ScrapRecord(
                material_name=material,
                weight_kg=weight,
                length_mm=length_mm,
                width_mm=width_mm,
                quantity=quantity,
                dimensions=dimensions,
                reason_code=reason,
                source_customer_id=customer_id,
                status="pending",
                created_by=user_id,
                created_at=datetime.utcnow(),
            )
            db.add(record)
            records_created.append(record)

            # Group by material and approximate dimensions
            group_key = f"{material}|{dimensions}"
            if group_key not in grouped_items:
                grouped_items[group_key] = {
                    "material_name": material,
                    "dimensions": dimensions,
                    "total_weight_kg": 0,
                    "total_quantity": 0,
                    "records": [],
                }
            grouped_items[group_key]["total_weight_kg"] += weight
            grouped_items[group_key]["total_quantity"] += quantity

        db.commit()

        grouped_list = list(grouped_items.values())

        return {
            "message": f"Imported {len(records_created)} scrap records",
            "records_count": len(records_created),
            "grouped_items": grouped_list,
            "total_weight_kg": sum(r.weight_kg for r in records_created),
        }


class ReusableStockService:
    """Service class for reusable stock operations."""

    @staticmethod
    def list_reusable_stock(
        db: Session,
        *,
        available_only: bool = True,
        material_name: Optional[str] = None,
        quality_grade: Optional[str] = None,
        min_length: Optional[float] = None,
        max_length: Optional[float] = None,
    ) -> List[models.ReusableStock]:
        """List reusable stock items with filters."""
        query = db.query(models.ReusableStock)

        if available_only:
            query = query.filter(models.ReusableStock.is_available == True)
        if material_name:
            query = query.filter(models.ReusableStock.material_name.ilike(f"%{material_name}%"))
        if quality_grade:
            query = query.filter(models.ReusableStock.quality_grade == quality_grade)
        if min_length:
            query = query.filter(models.ReusableStock.length_mm >= min_length)
        if max_length:
            query = query.filter(models.ReusableStock.length_mm <= max_length)

        return query.order_by(models.ReusableStock.created_at.desc()).all()

    @staticmethod
    def find_matching_reusable(
        db: Session,
        material_name: str,
        required_length_mm: float,
        tolerance_mm: float = 50,
    ) -> Dict[str, Any]:
        """Find reusable stock that matches required dimensions (for backfill)."""
        matches = (
            db.query(models.ReusableStock)
            .filter(
                models.ReusableStock.is_available == True,
                models.ReusableStock.material_name.ilike(f"%{material_name}%"),
                models.ReusableStock.length_mm >= required_length_mm - tolerance_mm,
            )
            .order_by(func.abs(models.ReusableStock.length_mm - required_length_mm))
            .limit(5)
            .all()
        )

        return {
            "required_length_mm": required_length_mm,
            "tolerance_mm": tolerance_mm,
            "matches": [
                {
                    "id": m.id,
                    "material_name": m.material_name,
                    "dimensions": m.dimensions,
                    "length_mm": m.length_mm,
                    "weight_kg": m.weight_kg,
                    "quality_grade": m.quality_grade,
                    "waste_mm": (m.length_mm or 0) - required_length_mm,
                }
                for m in matches
            ],
        }

    @staticmethod
    def create_reusable_stock(
        db: Session,
        *,
        material_name: str,
        dimensions: str,
        weight_kg: float,
        user_id: int,
        length_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
        quantity: int = 1,
        source_item_id: Optional[int] = None,
        source_customer_id: Optional[int] = None,
        quality_grade: str = "A",
        notes: Optional[str] = None,
    ) -> models.ReusableStock:
        """Add new reusable stock item."""
        if weight_kg <= 0:
            raise ValueError("Weight must be positive")

        stock = models.ReusableStock(
            material_name=material_name,
            dimensions=dimensions,
            weight_kg=weight_kg,
            length_mm=length_mm,
            width_mm=width_mm,
            quantity=quantity,
            source_item_id=source_item_id,
            source_customer_id=source_customer_id,
            quality_grade=quality_grade,
            notes=notes,
            is_available=True,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
        return stock

    @staticmethod
    def use_reusable_stock(
        db: Session,
        stock_id: int,
        production_item_id: int,
    ) -> Dict[str, Any]:
        """Mark reusable stock as used in a production item."""
        stock = db.query(models.ReusableStock).filter(models.ReusableStock.id == stock_id).first()
        if not stock:
            raise LookupError("Reusable stock not found")
        if not stock.is_available:
            raise ValueError("Stock already used")

        stock.is_available = False
        stock.used_in_item_id = production_item_id
        db.commit()
        return {"message": "Stock marked as used", "id": stock_id}

    @staticmethod
    def return_to_inventory(
        db: Session,
        stock_id: int,
    ) -> Dict[str, Any]:
        """Return reusable stock back to main inventory."""
        stock = db.query(models.ReusableStock).filter(models.ReusableStock.id == stock_id).first()
        if not stock:
            raise LookupError("Reusable stock not found")
        if not stock.is_available:
            raise ValueError("Stock already used, cannot return")

        inv = db.query(models.Inventory).filter(models.Inventory.name.ilike(f"%{stock.material_name}%")).first()

        if inv:
            inv.total = (inv.total or 0) + stock.weight_kg
        else:
            inv = models.Inventory(
                name=stock.material_name,
                unit="kg",
                total=stock.weight_kg,
                used=0,
                category="reusable",
                created_at=datetime.utcnow(),
            )
            db.add(inv)

        stock.is_available = False
        stock.notes = (stock.notes or "") + (f" [Returned to inventory {datetime.utcnow().strftime('%Y-%m-%d')}]")

        db.commit()
        return {
            "message": "Returned to main inventory",
            "material": stock.material_name,
            "weight_kg": stock.weight_kg,
        }

    @staticmethod
    def mark_as_scrap(
        db: Session,
        stock_id: int,
        reason: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """Mark reusable stock as scrap (when it can't be used)."""
        stock = db.query(models.ReusableStock).filter(models.ReusableStock.id == stock_id).first()
        if not stock:
            raise LookupError("Not found")

        scrap = models.ScrapRecord(
            material_name=stock.material_name,
            weight_kg=stock.weight_kg,
            length_mm=stock.length_mm,
            width_mm=stock.width_mm,
            quantity=stock.quantity,
            reason_code=reason,
            dimensions=stock.dimensions,
            status="pending",
            created_by=user_id,
        )
        db.add(scrap)
        stock.is_available = False
        db.commit()
        return {"message": "Moved to scrap", "scrap_id": scrap.id}

    @staticmethod
    def delete_reusable_stock(db: Session, stock_id: int) -> Dict[str, Any]:
        """Delete reusable stock item."""
        stock = db.query(models.ReusableStock).filter(models.ReusableStock.id == stock_id).first()
        if not stock:
            raise LookupError("Not found")

        db.delete(stock)
        db.commit()
        return {"message": "Deleted", "id": stock_id}


class ScrapAnalyticsService:
    """Service class for scrap analytics and reporting."""

    @staticmethod
    def calculate_scrap_analytics(
        db: Session,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get loss analytics and KPIs for dashboard."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Inventory totals
        inv = db.query(models.Inventory).all()
        total_input = sum(float(i.total or 0) for i in inv)
        total_consumed = sum(float(i.used or 0) for i in inv)

        # Scrap totals
        scrap = db.query(models.ScrapRecord).filter(models.ScrapRecord.created_at >= cutoff).all()
        total_scrap = sum(float(s.weight_kg or 0) for s in scrap)

        # Scrap by reason
        scrap_by_reason: Dict[str, float] = {}
        for s in scrap:
            reason = s.reason_code or "other"
            scrap_by_reason[reason] = scrap_by_reason.get(reason, 0) + float(s.weight_kg or 0)

        # Scrap by material
        scrap_by_material: Dict[str, float] = {}
        for s in scrap:
            mat = s.material_name or "Unknown"
            scrap_by_material[mat] = scrap_by_material.get(mat, 0) + float(s.weight_kg or 0)

        # Reusable totals
        reusable = db.query(models.ReusableStock).filter(models.ReusableStock.is_available == True).all()
        total_reusable = sum(float(r.weight_kg or 0) for r in reusable)

        # Calculate rates
        scrap_rate = (total_scrap / total_consumed * 100) if total_consumed > 0 else 0
        recovery_rate = (total_reusable / total_scrap * 100) if total_scrap > 0 else 0

        # Estimated loss value
        estimated_loss = total_scrap * DEFAULT_SCRAP_RATE_PER_KG

        return {
            "period_days": days,
            "total_input_kg": round(total_input, 2),
            "total_consumed_kg": round(total_consumed, 2),
            "total_scrap_kg": round(total_scrap, 2),
            "total_reusable_kg": round(total_reusable, 2),
            "scrap_rate_pct": round(scrap_rate, 2),
            "recovery_rate_pct": round(recovery_rate, 2),
            "scrap_by_reason": scrap_by_reason,
            "scrap_by_material": scrap_by_material,
            "estimated_loss_value": round(estimated_loss, 2),
        }

    @staticmethod
    def get_scrap_summary(db: Session) -> Dict[str, Any]:
        """Quick summary for dashboard widgets."""
        scrap_total = db.query(func.sum(models.ScrapRecord.weight_kg)).scalar() or 0
        scrap_pending = (
            db.query(func.sum(models.ScrapRecord.weight_kg)).filter(models.ScrapRecord.status == "pending").scalar()
            or 0
        )
        scrap_count = db.query(models.ScrapRecord).count()

        reusable_available = (
            db.query(func.sum(models.ReusableStock.weight_kg))
            .filter(models.ReusableStock.is_available == True)
            .scalar()
            or 0
        )
        reusable_count = db.query(models.ReusableStock).filter(models.ReusableStock.is_available == True).count()

        # Recent scrap (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_scrap = (
            db.query(func.sum(models.ScrapRecord.weight_kg)).filter(models.ScrapRecord.created_at >= week_ago).scalar()
            or 0
        )

        return {
            "scrap_total_kg": round(float(scrap_total), 2),
            "scrap_pending_kg": round(float(scrap_pending), 2),
            "scrap_records_count": scrap_count,
            "reusable_available_kg": round(float(reusable_available), 2),
            "reusable_items_count": reusable_count,
            "recent_scrap_kg": round(float(recent_scrap), 2),
        }

    @staticmethod
    def bulk_scrap_action(
        db: Session,
        action: str,
        record_ids: List[int],
        user_id: int,
    ) -> Dict[str, Any]:
        """Perform bulk action on multiple scrap records."""
        records = db.query(models.ScrapRecord).filter(models.ScrapRecord.id.in_(record_ids)).all()

        if not records:
            raise LookupError("No records found")

        results: List[Dict[str, Any]] = []

        for record in records:
            if action == "return_to_inventory":
                inv = (
                    db.query(models.Inventory).filter(models.Inventory.name.ilike(f"%{record.material_name}%")).first()
                )
                if inv:
                    inv.total = (inv.total or 0) + record.weight_kg
                else:
                    inv = models.Inventory(
                        name=record.material_name,
                        unit="kg",
                        total=record.weight_kg,
                        used=0,
                        category="reusable",
                    )
                    db.add(inv)
                record.status = "returned_to_inventory"
                results.append({"id": record.id, "action": "returned"})

            elif action == "dispose":
                record.status = "disposed"
                results.append({"id": record.id, "action": "disposed"})

            elif action == "mark_reusable":
                reusable = models.ReusableStock(
                    material_name=record.material_name,
                    dimensions=record.dimensions or "",
                    weight_kg=record.weight_kg,
                    length_mm=record.length_mm,
                    width_mm=record.width_mm,
                    quantity=record.quantity,
                    quality_grade="B",
                    is_available=True,
                    created_by=user_id,
                )
                db.add(reusable)
                record.status = "returned_to_inventory"
                results.append({"id": record.id, "action": "moved_to_reusable"})

        db.commit()
        return {"message": f"Processed {len(results)} records", "results": results}
