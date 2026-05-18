"""
Stock Valuation Service
=======================
Calculates stock valuation using FIFO or weighted-average methods.
Populates valuation fields on StockMovement records.

All monetary values use Decimal for precision.
Indian fiscal year: April to March (e.g., Apr 2025 - Mar 2026 = "FY2526").
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy.orm import Session

from ..models_v2 import (
    MaterialMaster,
    StockLot,
    StockMovement,
)

ZERO = Decimal("0")
ZERO_2 = Decimal("0.00")
ZERO_3 = Decimal("0.000")
ZERO_4 = Decimal("0.0000")


class StockValuationService:
    """Calculates stock valuation using FIFO or weighted-average methods."""

    @staticmethod
    def get_fiscal_year(d: date) -> str:
        """Return Indian fiscal year string.

        Indian FY runs April-March.
        Apr 2025 - Mar 2026 => "FY2526"
        Jan 2025 - Mar 2025 => "FY2425"
        """
        if d.month >= 4:
            start_year = d.year
        else:
            start_year = d.year - 1
        end_year = start_year + 1
        return f"FY{start_year % 100:02d}{end_year % 100:02d}"

    @staticmethod
    def get_valuation_rate_for_lot(lot: StockLot) -> Decimal:
        """Get valuation rate for a specific lot (from purchase_rate).

        Returns Decimal("0") when purchase_rate is None or zero.
        """
        if lot.purchase_rate is not None and lot.purchase_rate > 0:
            return Decimal(str(lot.purchase_rate)).quantize(ZERO_4, rounding=ROUND_HALF_UP)
        return ZERO

    @staticmethod
    def _get_latest_balance(db: Session, material_id: int) -> tuple[Decimal, Decimal]:
        """Return (balance_qty_kg, balance_stock_value) from the most recent
        movement across all lots of the given material.

        Falls back to computing from active lots when no prior valued movement exists.
        """
        latest = (
            db.query(StockMovement)
            .join(StockLot, StockMovement.stock_lot_id == StockLot.id)
            .filter(
                StockLot.material_id == material_id,
                StockMovement.balance_qty_kg.isnot(None),
            )
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .first()
        )
        if latest is not None:
            return (
                Decimal(str(latest.balance_qty_kg)),
                Decimal(str(latest.balance_stock_value or 0)),
            )
        # Cold start: compute from active lots
        rows = db.query(StockLot).filter(StockLot.material_id == material_id, StockLot.is_active == True).all()
        total_qty = ZERO
        total_val = ZERO
        for lot in rows:
            qty = Decimal(str(lot.current_weight_kg))
            rate = StockValuationService.get_valuation_rate_for_lot(lot)
            total_qty += qty
            total_val += (qty * rate).quantize(ZERO_2, rounding=ROUND_HALF_UP)
        return total_qty, total_val

    @staticmethod
    def record_valuation_on_movement(
        db: Session,
        movement: StockMovement,
        lot: StockLot,
        posting_date_override: Optional[date] = None,
    ) -> None:
        """Populate valuation fields on a stock movement record.

        Parameters
        ----------
        db : Session
        movement : StockMovement  (already added to session, not yet committed)
        lot : StockLot            (the lot this movement belongs to)
        posting_date_override : date, optional
            Allows backdating; defaults to today.
        """
        valuation_rate = StockValuationService.get_valuation_rate_for_lot(lot)
        movement.valuation_rate = valuation_rate

        weight_change = Decimal(str(movement.weight_change_kg))
        stock_value_change = (weight_change * valuation_rate).quantize(ZERO_2, rounding=ROUND_HALF_UP)
        movement.stock_value_change = stock_value_change

        # Running balances (material-level)
        prev_qty, prev_val = StockValuationService._get_latest_balance(db, lot.material_id)
        new_qty = (prev_qty + weight_change).quantize(ZERO_3, rounding=ROUND_HALF_UP)
        new_val = (prev_val + stock_value_change).quantize(ZERO_2, rounding=ROUND_HALF_UP)

        # Guard against negative values from rounding
        if new_qty < ZERO:
            new_qty = ZERO_3
        if new_val < ZERO:
            new_val = ZERO_2

        movement.balance_qty_kg = new_qty
        movement.balance_stock_value = new_val

        # Posting date and fiscal year
        p_date = posting_date_override or date.today()
        movement.posting_date = p_date
        movement.fiscal_year = StockValuationService.get_fiscal_year(p_date)

    # -----------------------------------------------------------------
    # Valuation reports
    # -----------------------------------------------------------------

    @staticmethod
    def calculate_fifo_valuation(db: Session, material_id: int) -> dict:
        """Calculate current stock value using FIFO method.

        Looks at all active lots ordered by received_date ascending (oldest
        first).  Each lot's value = current_weight_kg * purchase_rate.

        Returns
        -------
        dict with keys: total_qty_kg, total_value, valuation_rate_per_kg,
                        lot_breakdown (list of dicts)
        """
        lots = (
            db.query(StockLot)
            .filter(
                StockLot.material_id == material_id,
                StockLot.is_active == True,
            )
            .order_by(StockLot.received_date.asc())
            .all()
        )

        total_qty = ZERO
        total_value = ZERO
        breakdown = []

        for lot in lots:
            qty = Decimal(str(lot.current_weight_kg))
            rate = StockValuationService.get_valuation_rate_for_lot(lot)
            value = (qty * rate).quantize(ZERO_2, rounding=ROUND_HALF_UP)

            total_qty += qty
            total_value += value

            breakdown.append(
                {
                    "lot_id": lot.id,
                    "lot_number": lot.lot_number,
                    "received_date": lot.received_date,
                    "current_weight_kg": float(qty),
                    "purchase_rate": float(rate),
                    "lot_value": float(value),
                }
            )

        avg_rate = ZERO
        if total_qty > 0:
            avg_rate = (total_value / total_qty).quantize(ZERO_4, rounding=ROUND_HALF_UP)

        return {
            "total_qty_kg": float(total_qty),
            "total_value": float(total_value),
            "valuation_rate_per_kg": float(avg_rate),
            "lot_breakdown": breakdown,
        }

    @staticmethod
    def calculate_weighted_avg_valuation(db: Session, material_id: int) -> dict:
        """Calculate current stock value using weighted average.

        weighted_avg = SUM(lot.current_weight_kg * lot.purchase_rate)
                       / SUM(lot.current_weight_kg)

        Returns
        -------
        dict with keys: total_qty_kg, total_value, avg_rate_per_kg
        """
        lots = (
            db.query(StockLot)
            .filter(
                StockLot.material_id == material_id,
                StockLot.is_active == True,
            )
            .all()
        )

        total_qty = ZERO
        total_value = ZERO

        for lot in lots:
            qty = Decimal(str(lot.current_weight_kg))
            rate = StockValuationService.get_valuation_rate_for_lot(lot)
            total_qty += qty
            total_value += (qty * rate).quantize(ZERO_2, rounding=ROUND_HALF_UP)

        avg_rate = ZERO
        if total_qty > 0:
            avg_rate = (total_value / total_qty).quantize(ZERO_4, rounding=ROUND_HALF_UP)

        return {
            "total_qty_kg": float(total_qty),
            "total_value": float(total_value),
            "avg_rate_per_kg": float(avg_rate),
        }

    @staticmethod
    def get_stock_value_summary(db: Session, method: str = "fifo") -> list[dict]:
        """Summary of stock value by material. Used for dashboard/reports.

        Parameters
        ----------
        method : str
            "fifo" or "weighted_avg"

        Returns
        -------
        list of dicts, one per material with stock.
        """
        # Find materials that have at least one active lot
        material_ids = db.query(StockLot.material_id).filter(StockLot.is_active == True).distinct().all()

        results = []
        for (material_id,) in material_ids:
            mat = db.query(MaterialMaster).filter(MaterialMaster.id == material_id).first()
            if mat is None:
                continue

            if method == "weighted_avg":
                val = StockValuationService.calculate_weighted_avg_valuation(db, material_id)
                rate_key = "avg_rate_per_kg"
            else:
                val = StockValuationService.calculate_fifo_valuation(db, material_id)
                rate_key = "valuation_rate_per_kg"

            results.append(
                {
                    "material_id": material_id,
                    "material_code": mat.code,
                    "material_name": mat.name,
                    "total_qty_kg": val["total_qty_kg"],
                    "total_value": val["total_value"],
                    "rate_per_kg": val[rate_key],
                    "method": method,
                }
            )

        return results
