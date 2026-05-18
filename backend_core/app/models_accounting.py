"""
Accounting Models for KBSteel ERP
==================================
Double-entry ledger inspired by ERPNext GL Entry pattern.

Tables:
- accounts: Chart of Accounts (hierarchical)
- fiscal_years: Financial year tracking
- journal_entries: Header for accounting entries
- journal_entry_lines: Debit/credit lines
- cost_centers: Cost allocation centers

Feature-flagged via ACCOUNTING_ENABLED env var (default: false).
All entries created in shadow/draft mode (is_posted=False) by default.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class Account(Base):
    """Chart of Accounts -- hierarchical."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)  # e.g., "1100"
    name = Column(String(100), nullable=False)  # e.g., "Stock In Hand"
    account_type = Column(String(20))  # asset, liability, equity, income, expense
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    is_group = Column(Boolean, default=False)  # parent vs leaf
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalEntryLine", back_populates="account")

    __table_args__ = (
        Index("ix_account_type", "account_type"),
        Index("ix_account_parent", "parent_id"),
    )


class FiscalYear(Base):
    """Financial year tracking."""

    __tablename__ = "fiscal_years"

    id = Column(Integer, primary_key=True)
    name = Column(String(10), unique=True, nullable=False)  # "FY2526"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class JournalEntry(Base):
    """Header for a double-entry accounting entry."""

    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    entry_number = Column(String(50), unique=True, nullable=False)
    posting_date = Column(Date, nullable=False)
    fiscal_year = Column(String(10))
    reference_type = Column(String(50))  # "StockMovement", "GRN", "Dispatch"
    reference_id = Column(Integer)
    narration = Column(String(500))
    is_posted = Column(Boolean, default=False)  # False = shadow/draft
    total_debit = Column(Numeric(15, 2), default=0)
    total_credit = Column(Numeric(15, 2), default=0)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    lines = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_je_posting_date", "posting_date"),
        Index("ix_je_reference", "reference_type", "reference_id"),
        Index("ix_je_fiscal_year", "fiscal_year"),
    )


class JournalEntryLine(Base):
    """Individual debit/credit line within a journal entry."""

    __tablename__ = "journal_entry_lines"

    id = Column(Integer, primary_key=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)
    cost_center = Column(String(50), nullable=True)

    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")

    __table_args__ = (
        Index("ix_jel_account", "account_id"),
        Index("ix_jel_journal", "journal_entry_id"),
    )


class CostCenter(Base):
    """Cost allocation center for management accounting."""

    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
