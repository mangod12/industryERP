"""
Accounting Service for KBSteel ERP
====================================
Auto-creates double-entry journal entries from stock movements.

Feature-flagged: set ACCOUNTING_ENABLED=true to activate.
All entries created as is_posted=False (shadow/draft mode) by default.
Uses Decimal for all monetary values -- never float.
"""

import os
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models_accounting import (
    Account,
    JournalEntry,
    JournalEntryLine,
)
from ..models_v2 import MovementType, StockMovement

ACCOUNTING_ENABLED = os.environ.get("ACCOUNTING_ENABLED", "false").lower() == "true"

ZERO = Decimal("0")
ZERO_2 = Decimal("0.00")

# ── Default Chart of Accounts for Indian steel business ──────────────

DEFAULT_ACCOUNTS = [
    {"code": "1000", "name": "Assets", "type": "asset", "is_group": True, "parent": None},
    {"code": "1100", "name": "Stock In Hand", "type": "asset", "is_group": False, "parent": "1000"},
    {"code": "1200", "name": "Work In Progress", "type": "asset", "is_group": False, "parent": "1000"},
    {"code": "2000", "name": "Liabilities", "type": "liability", "is_group": True, "parent": None},
    {"code": "2100", "name": "Vendor Payable", "type": "liability", "is_group": False, "parent": "2000"},
    {"code": "3000", "name": "Equity", "type": "equity", "is_group": True, "parent": None},
    {"code": "4000", "name": "Income", "type": "income", "is_group": True, "parent": None},
    {"code": "4100", "name": "Sales", "type": "income", "is_group": False, "parent": "4000"},
    {"code": "5000", "name": "Expenses", "type": "expense", "is_group": True, "parent": None},
    {"code": "5100", "name": "Cost of Goods Sold", "type": "expense", "is_group": False, "parent": "5000"},
    {"code": "5200", "name": "Scrap Loss", "type": "expense", "is_group": False, "parent": "5000"},
    {"code": "5300", "name": "Stock Adjustment", "type": "expense", "is_group": False, "parent": "5000"},
]

# Movement type → (debit account code, credit account code)
# Positive value_change means debit first account, credit second.
# For adjustments direction depends on sign -- handled in code.
MOVEMENT_ACCOUNT_MAP: dict[str, tuple[str, str]] = {
    MovementType.INWARD_PURCHASE.value: ("1100", "2100"),  # DR Stock, CR Vendor Payable
    MovementType.INWARD_RETURN.value: ("1100", "2100"),  # DR Stock, CR Vendor Payable
    MovementType.CONSUMPTION.value: ("5100", "1100"),  # DR COGS, CR Stock
    MovementType.OUTWARD_SALE.value: ("5100", "1100"),  # DR COGS, CR Stock
    MovementType.OUTWARD_SCRAP.value: ("5200", "1100"),  # DR Scrap Loss, CR Stock
    MovementType.ADJUSTMENT_PLUS.value: ("1100", "5300"),  # DR Stock, CR Stock Adj
    MovementType.ADJUSTMENT_MINUS.value: ("5300", "1100"),  # DR Stock Adj, CR Stock
}

# Movement types that should NOT generate journal entries
SKIP_MOVEMENT_TYPES = {
    MovementType.INWARD_TRANSFER.value,
    MovementType.OUTWARD_TRANSFER.value,
    MovementType.REWEIGH.value,
    MovementType.SPLIT.value,
    MovementType.MERGE.value,
}


def _get_fiscal_year(d: date) -> str:
    """Return Indian fiscal year string. Apr-Mar cycle."""
    if d.month >= 4:
        return f"FY{d.year % 100:02d}{(d.year + 1) % 100:02d}"
    return f"FY{(d.year - 1) % 100:02d}{d.year % 100:02d}"


class AccountingService:
    """Double-entry accounting service for stock movements."""

    @staticmethod
    def seed_default_accounts(db: Session) -> list[Account]:
        """Create default chart of accounts if the accounts table is empty.

        Returns the list of created Account objects.
        """
        existing_count = db.query(func.count(Account.id)).scalar()
        if existing_count > 0:
            return []

        # First pass: create all accounts without parent links
        code_to_account: dict[str, Account] = {}
        created: list[Account] = []

        for acct_def in DEFAULT_ACCOUNTS:
            account = Account(
                code=acct_def["code"],
                name=acct_def["name"],
                account_type=acct_def["type"],
                is_group=acct_def.get("is_group", False),
                is_active=True,
            )
            db.add(account)
            code_to_account[acct_def["code"]] = account
            created.append(account)

        db.flush()  # assign IDs

        # Second pass: set parent_id references
        for acct_def in DEFAULT_ACCOUNTS:
            parent_code = acct_def.get("parent")
            if parent_code and parent_code in code_to_account:
                code_to_account[acct_def["code"]].parent_id = code_to_account[parent_code].id

        db.flush()
        return created

    @staticmethod
    def get_account_by_code(db: Session, code: str) -> Optional[Account]:
        """Look up an account by its code."""
        return db.query(Account).filter(Account.code == code).first()

    @staticmethod
    def _next_entry_number(db: Session) -> str:
        """Generate the next journal entry number."""
        max_id = db.query(func.count(JournalEntry.id)).scalar() or 0
        return f"JE-{max_id + 1:06d}"

    @staticmethod
    def create_journal_entry(
        db: Session,
        posting_date: date,
        reference_type: str,
        reference_id: int,
        narration: str,
        lines: list[dict],
        is_posted: bool = False,
        created_by: str = "system",
    ) -> JournalEntry:
        """Create a balanced journal entry.

        Each item in *lines* must have keys:
            account_code: str
            debit: Decimal
            credit: Decimal
            cost_center: str | None  (optional)

        Raises ValueError if total debits != total credits.
        """
        total_debit = ZERO
        total_credit = ZERO
        entry_lines: list[JournalEntryLine] = []

        for line in lines:
            debit = Decimal(str(line.get("debit", 0))).quantize(ZERO_2, rounding=ROUND_HALF_UP)
            credit = Decimal(str(line.get("credit", 0))).quantize(ZERO_2, rounding=ROUND_HALF_UP)
            total_debit += debit
            total_credit += credit

            account = AccountingService.get_account_by_code(db, line["account_code"])
            if account is None:
                raise ValueError(f"Account with code '{line['account_code']}' not found")

            entry_lines.append(
                JournalEntryLine(
                    account_id=account.id,
                    debit=debit,
                    credit=credit,
                    cost_center=line.get("cost_center"),
                )
            )

        if total_debit != total_credit:
            raise ValueError(f"Unbalanced entry: total_debit={total_debit}, total_credit={total_credit}")

        fiscal_year = _get_fiscal_year(posting_date)

        entry = JournalEntry(
            entry_number=AccountingService._next_entry_number(db),
            posting_date=posting_date,
            fiscal_year=fiscal_year,
            reference_type=reference_type,
            reference_id=reference_id,
            narration=narration,
            is_posted=is_posted,
            total_debit=total_debit,
            total_credit=total_credit,
            created_by=created_by,
        )
        db.add(entry)
        db.flush()

        for el in entry_lines:
            el.journal_entry_id = entry.id
            db.add(el)

        db.flush()
        return entry

    @staticmethod
    def create_entry_for_stock_movement(db: Session, movement: StockMovement) -> Optional[JournalEntry]:
        """Auto-create a shadow journal entry for a stock movement.

        Movement type -> accounting entry mapping:
        - INWARD (GRN):     DR Stock In Hand, CR Vendor Payable
        - CONSUMPTION:      DR COGS, CR Stock In Hand
        - OUTWARD_SALE:     DR COGS, CR Stock In Hand
        - OUTWARD_SCRAP:    DR Scrap Loss, CR Stock In Hand
        - ADJUSTMENT (+):   DR Stock In Hand, CR Stock Adjustment
        - ADJUSTMENT (-):   DR Stock Adjustment, CR Stock In Hand
        - TRANSFER/SPLIT/MERGE/REWEIGH: No entry

        Returns None if the movement type has no accounting mapping or if
        the value is zero.
        """
        mv_type = (
            movement.movement_type.value if hasattr(movement.movement_type, "value") else str(movement.movement_type)
        )

        if mv_type in SKIP_MOVEMENT_TYPES:
            return None

        mapping = MOVEMENT_ACCOUNT_MAP.get(mv_type)
        if mapping is None:
            return None

        debit_code, credit_code = mapping

        # Determine the absolute monetary value
        value_change = movement.stock_value_change
        if value_change is None or value_change == 0:
            # Fall back to weight * valuation_rate
            rate = Decimal(str(movement.valuation_rate or 0))
            weight = abs(Decimal(str(movement.weight_change_kg)))
            value_change = (weight * rate).quantize(ZERO_2, rounding=ROUND_HALF_UP)

        amount = abs(Decimal(str(value_change))).quantize(ZERO_2, rounding=ROUND_HALF_UP)

        if amount <= ZERO:
            return None

        posting_date = movement.posting_date or date.today()

        lines = [
            {"account_code": debit_code, "debit": amount, "credit": ZERO},
            {"account_code": credit_code, "debit": ZERO, "credit": amount},
        ]

        return AccountingService.create_journal_entry(
            db=db,
            posting_date=posting_date,
            reference_type="StockMovement",
            reference_id=movement.id,
            narration=(f"Auto entry for {mv_type} movement #{movement.movement_number}"),
            lines=lines,
            is_posted=False,  # Always shadow mode
            created_by="system",
        )

    @staticmethod
    def post_entries(db: Session, entry_ids: list[int]) -> list[JournalEntry]:
        """Mark journal entries as posted (admin action).

        Returns the list of posted entries.
        """
        entries = db.query(JournalEntry).filter(JournalEntry.id.in_(entry_ids)).all()
        for entry in entries:
            entry.is_posted = True
        db.flush()
        return entries

    @staticmethod
    def get_trial_balance(db: Session, fiscal_year: Optional[str] = None) -> list[dict]:
        """Trial balance report: account, total_debit, total_credit, balance.

        Aggregates all posted journal entry lines grouped by account.
        If fiscal_year is provided, filters to that fiscal year only.
        """
        query = (
            db.query(
                Account.code,
                Account.name,
                Account.account_type,
                func.coalesce(func.sum(JournalEntryLine.debit), 0).label("total_debit"),
                func.coalesce(func.sum(JournalEntryLine.credit), 0).label("total_credit"),
            )
            .join(
                JournalEntryLine,
                JournalEntryLine.account_id == Account.id,
            )
            .join(
                JournalEntry,
                JournalEntry.id == JournalEntryLine.journal_entry_id,
            )
            .filter(JournalEntry.is_posted == True)  # noqa: E712
        )

        if fiscal_year:
            query = query.filter(JournalEntry.fiscal_year == fiscal_year)

        query = query.group_by(Account.code, Account.name, Account.account_type)
        query = query.order_by(Account.code)

        results = []
        for row in query.all():
            total_debit = Decimal(str(row.total_debit))
            total_credit = Decimal(str(row.total_credit))
            balance = total_debit - total_credit
            results.append(
                {
                    "account_code": row.code,
                    "account_name": row.name,
                    "account_type": row.account_type,
                    "total_debit": float(total_debit),
                    "total_credit": float(total_credit),
                    "balance": float(balance),
                }
            )

        return results
