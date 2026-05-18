"""
Tests for the Accounting Service
=================================
Covers:
- Seed default accounts
- Create balanced journal entry
- Reject unbalanced entry
- Auto journal entries from stock movements (GRN, consumption, scrap, adjustment)
- Shadow mode (is_posted=False by default)
- Post entries
- Trial balance
- Feature flag off: no entries created
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# We need models_v3 imported so all tables are registered on Base
from backend_core.app import (
    models_accounting,  # noqa: F401
    models_v3,  # noqa: F401
)
from backend_core.app.db import Base
from backend_core.app.models_accounting import (
    Account,
    JournalEntry,
)
from backend_core.app.models_v2 import (
    MaterialMaster,
    MaterialType,
    MovementType,
    QAStatus,
    StockLot,
    StockMovement,
    Vendor,
)
from backend_core.app.services.accounting_service import (
    ACCOUNTING_ENABLED,
    DEFAULT_ACCOUNTS,
    AccountingService,
)

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def engine():
    """In-memory SQLite engine with all tables."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    """Transactional session that rolls back after each test."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def seeded_db(db):
    """DB with default accounts already seeded."""
    AccountingService.seed_default_accounts(db)
    db.commit()
    return db


def _create_user(db):
    """Create a minimal user row for FK constraints."""
    from backend_core.app.models import User
    from backend_core.app.security import hash_password

    user = User(
        username="acc_test_user",
        email="acc@test.com",
        hashed_password=hash_password("TestPass1!"),
        role="Boss",
        company="Test Steel",
    )
    db.add(user)
    db.flush()
    return user


def _create_material(db):
    mat = MaterialMaster(
        code="MAT-ACC-001",
        name="Test Plate",
        material_type=MaterialType.PLATE,
    )
    db.add(mat)
    db.flush()
    return mat


def _create_vendor(db):
    vendor = Vendor(code="V-ACC-001", name="Test Vendor")
    db.add(vendor)
    db.flush()
    return vendor


def _create_stock_lot(db, material, vendor, user, weight=Decimal("1000.000")):
    lot = StockLot(
        lot_number=f"LOT-ACC-{id(material)}",
        material_id=material.id,
        vendor_id=vendor.id,
        gross_weight_kg=weight + Decimal("10"),
        tare_weight_kg=Decimal("10"),
        net_weight_kg=weight,
        current_weight_kg=weight,
        received_date=datetime.utcnow(),
        qa_status=QAStatus.APPROVED,
        purchase_rate=Decimal("50.00"),  # Rs 50 per kg
    )
    db.add(lot)
    db.flush()
    return lot


def _create_movement(
    db,
    lot,
    user,
    movement_type,
    weight_change,
    movement_number=None,
):
    """Create a StockMovement with valuation fields populated."""
    weight_before = lot.current_weight_kg
    weight_after = weight_before + weight_change

    mv = StockMovement(
        movement_number=movement_number or f"MOV-ACC-{id(lot)}-{movement_type.value}",
        stock_lot_id=lot.id,
        movement_type=movement_type,
        weight_change_kg=weight_change,
        weight_before_kg=weight_before,
        weight_after_kg=weight_after,
        created_by=user.id,
        movement_date=datetime.utcnow(),
        posting_date=date.today(),
        fiscal_year="FY2526",
        valuation_rate=lot.purchase_rate,
        stock_value_change=(weight_change * lot.purchase_rate).quantize(Decimal("0.00")),
    )
    db.add(mv)
    db.flush()
    return mv


# ── Tests: Seed Accounts ────────────────────────────────────────────


class TestSeedAccounts:
    def test_seed_creates_correct_count(self, db):
        accounts = AccountingService.seed_default_accounts(db)
        assert len(accounts) == len(DEFAULT_ACCOUNTS)

    def test_seed_creates_hierarchy(self, db):
        AccountingService.seed_default_accounts(db)
        db.commit()

        stock = db.query(Account).filter(Account.code == "1100").first()
        assert stock is not None
        assert stock.name == "Stock In Hand"
        assert stock.parent is not None
        assert stock.parent.code == "1000"
        assert stock.parent.is_group is True

    def test_seed_is_idempotent(self, db):
        first = AccountingService.seed_default_accounts(db)
        db.commit()
        second = AccountingService.seed_default_accounts(db)
        assert len(first) == len(DEFAULT_ACCOUNTS)
        assert len(second) == 0  # No new accounts created


# ── Tests: Journal Entry Creation ────────────────────────────────────


class TestCreateJournalEntry:
    def test_balanced_entry_succeeds(self, seeded_db):
        db = seeded_db
        entry = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 6, 15),
            reference_type="Manual",
            reference_id=0,
            narration="Test balanced entry",
            lines=[
                {"account_code": "1100", "debit": Decimal("10000"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("10000")},
            ],
        )
        db.commit()

        assert entry.id is not None
        assert entry.total_debit == Decimal("10000.00")
        assert entry.total_credit == Decimal("10000.00")
        assert entry.fiscal_year == "FY2526"
        assert len(entry.lines) == 2

    def test_unbalanced_entry_raises(self, seeded_db):
        db = seeded_db
        with pytest.raises(ValueError, match="Unbalanced entry"):
            AccountingService.create_journal_entry(
                db=db,
                posting_date=date(2025, 6, 15),
                reference_type="Manual",
                reference_id=0,
                narration="Unbalanced",
                lines=[
                    {"account_code": "1100", "debit": Decimal("5000"), "credit": Decimal("0")},
                    {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("3000")},
                ],
            )

    def test_nonexistent_account_raises(self, seeded_db):
        db = seeded_db
        with pytest.raises(ValueError, match="not found"):
            AccountingService.create_journal_entry(
                db=db,
                posting_date=date(2025, 6, 15),
                reference_type="Manual",
                reference_id=0,
                narration="Bad account",
                lines=[
                    {"account_code": "9999", "debit": Decimal("100"), "credit": Decimal("0")},
                    {"account_code": "1100", "debit": Decimal("0"), "credit": Decimal("100")},
                ],
            )


# ── Tests: Auto Entries from Stock Movements ─────────────────────────


class TestStockMovementEntries:
    def test_grn_inward_creates_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(db, lot, user, MovementType.INWARD_PURCHASE, Decimal("1000.000"))
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        db.commit()

        assert entry is not None
        assert entry.reference_type == "StockMovement"
        assert entry.reference_id == movement.id
        assert entry.is_posted is False  # shadow mode

        # DR Stock In Hand (1100), CR Vendor Payable (2100)
        lines = sorted(entry.lines, key=lambda line: line.account.code)
        assert lines[0].account.code == "1100"
        assert lines[0].debit == Decimal("50000.00")  # 1000 kg * 50/kg
        assert lines[0].credit == Decimal("0.00")
        assert lines[1].account.code == "2100"
        assert lines[1].debit == Decimal("0.00")
        assert lines[1].credit == Decimal("50000.00")

    def test_consumption_creates_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.CONSUMPTION,
            Decimal("-200.000"),
            movement_number="MOV-CONS-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        db.commit()

        assert entry is not None
        lines = sorted(entry.lines, key=lambda line: line.account.code)
        # DR COGS (5100), CR Stock In Hand (1100)
        assert lines[0].account.code == "1100"
        assert lines[0].credit == Decimal("10000.00")  # 200 * 50
        assert lines[1].account.code == "5100"
        assert lines[1].debit == Decimal("10000.00")

    def test_scrap_creates_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.OUTWARD_SCRAP,
            Decimal("-100.000"),
            movement_number="MOV-SCRAP-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        db.commit()

        assert entry is not None
        lines = sorted(entry.lines, key=lambda line: line.account.code)
        # DR Scrap Loss (5200), CR Stock In Hand (1100)
        assert lines[0].account.code == "1100"
        assert lines[0].credit == Decimal("5000.00")  # 100 * 50
        assert lines[1].account.code == "5200"
        assert lines[1].debit == Decimal("5000.00")

    def test_adjustment_plus_creates_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.ADJUSTMENT_PLUS,
            Decimal("50.000"),
            movement_number="MOV-ADJP-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        db.commit()

        assert entry is not None
        lines = sorted(entry.lines, key=lambda line: line.account.code)
        # DR Stock In Hand (1100), CR Stock Adjustment (5300)
        assert lines[0].account.code == "1100"
        assert lines[0].debit == Decimal("2500.00")  # 50 * 50
        assert lines[1].account.code == "5300"
        assert lines[1].credit == Decimal("2500.00")

    def test_adjustment_minus_creates_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.ADJUSTMENT_MINUS,
            Decimal("-30.000"),
            movement_number="MOV-ADJM-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        db.commit()

        assert entry is not None
        lines = sorted(entry.lines, key=lambda line: line.account.code)
        # DR Stock Adjustment (5300), CR Stock In Hand (1100)
        assert lines[0].account.code == "1100"
        assert lines[0].credit == Decimal("1500.00")  # 30 * 50
        assert lines[1].account.code == "5300"
        assert lines[1].debit == Decimal("1500.00")

    def test_transfer_creates_no_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.INWARD_TRANSFER,
            Decimal("0.000"),
            movement_number="MOV-XFER-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        assert entry is None

    def test_split_creates_no_entry(self, seeded_db):
        db = seeded_db
        user = _create_user(db)
        mat = _create_material(db)
        vendor = _create_vendor(db)
        lot = _create_stock_lot(db, mat, vendor, user)
        movement = _create_movement(
            db,
            lot,
            user,
            MovementType.SPLIT,
            Decimal("-500.000"),
            movement_number="MOV-SPLIT-001",
        )
        db.commit()

        entry = AccountingService.create_entry_for_stock_movement(db, movement)
        assert entry is None


# ── Tests: Shadow Mode & Posting ─────────────────────────────────────


class TestShadowModeAndPosting:
    def test_entries_default_to_not_posted(self, seeded_db):
        db = seeded_db
        entry = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 7, 1),
            reference_type="Test",
            reference_id=1,
            narration="Shadow test",
            lines=[
                {"account_code": "1100", "debit": Decimal("100"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("100")},
            ],
        )
        db.commit()
        assert entry.is_posted is False

    def test_post_entries_marks_posted(self, seeded_db):
        db = seeded_db
        entry = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 7, 1),
            reference_type="Test",
            reference_id=1,
            narration="To be posted",
            lines=[
                {"account_code": "1100", "debit": Decimal("100"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("100")},
            ],
        )
        db.commit()

        posted = AccountingService.post_entries(db, [entry.id])
        db.commit()

        assert len(posted) == 1
        assert posted[0].is_posted is True

        # Verify via fresh query
        refreshed = db.query(JournalEntry).filter(JournalEntry.id == entry.id).first()
        assert refreshed.is_posted is True


# ── Tests: Trial Balance ─────────────────────────────────────────────


class TestTrialBalance:
    def test_trial_balance_aggregation(self, seeded_db):
        db = seeded_db

        # Create and POST two entries
        e1 = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 6, 1),
            reference_type="Test",
            reference_id=1,
            narration="Entry 1",
            lines=[
                {"account_code": "1100", "debit": Decimal("10000"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("10000")},
            ],
        )
        e2 = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 7, 1),
            reference_type="Test",
            reference_id=2,
            narration="Entry 2",
            lines=[
                {"account_code": "5100", "debit": Decimal("3000"), "credit": Decimal("0")},
                {"account_code": "1100", "debit": Decimal("0"), "credit": Decimal("3000")},
            ],
        )
        AccountingService.post_entries(db, [e1.id, e2.id])
        db.commit()

        tb = AccountingService.get_trial_balance(db)
        assert len(tb) == 3  # 1100, 2100, 5100

        by_code = {row["account_code"]: row for row in tb}

        # Stock In Hand: DR 10000, CR 3000, balance 7000
        assert by_code["1100"]["total_debit"] == 10000.0
        assert by_code["1100"]["total_credit"] == 3000.0
        assert by_code["1100"]["balance"] == 7000.0

        # Vendor Payable: DR 0, CR 10000, balance -10000
        assert by_code["2100"]["total_debit"] == 0.0
        assert by_code["2100"]["total_credit"] == 10000.0
        assert by_code["2100"]["balance"] == -10000.0

        # COGS: DR 3000, CR 0, balance 3000
        assert by_code["5100"]["total_debit"] == 3000.0
        assert by_code["5100"]["total_credit"] == 0.0
        assert by_code["5100"]["balance"] == 3000.0

    def test_trial_balance_filters_by_fiscal_year(self, seeded_db):
        db = seeded_db

        # FY2526 entry (June 2025)
        e1 = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 6, 1),
            reference_type="Test",
            reference_id=1,
            narration="FY2526",
            lines=[
                {"account_code": "1100", "debit": Decimal("5000"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("5000")},
            ],
        )
        # FY2627 entry (May 2026)
        e2 = AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2026, 5, 1),
            reference_type="Test",
            reference_id=2,
            narration="FY2627",
            lines=[
                {"account_code": "1100", "debit": Decimal("8000"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("8000")},
            ],
        )
        AccountingService.post_entries(db, [e1.id, e2.id])
        db.commit()

        tb_2526 = AccountingService.get_trial_balance(db, fiscal_year="FY2526")
        by_code = {row["account_code"]: row for row in tb_2526}
        assert by_code["1100"]["total_debit"] == 5000.0

        tb_2627 = AccountingService.get_trial_balance(db, fiscal_year="FY2627")
        by_code2 = {row["account_code"]: row for row in tb_2627}
        assert by_code2["1100"]["total_debit"] == 8000.0

    def test_unposted_entries_excluded_from_trial_balance(self, seeded_db):
        db = seeded_db

        AccountingService.create_journal_entry(
            db=db,
            posting_date=date(2025, 6, 1),
            reference_type="Test",
            reference_id=1,
            narration="Not posted",
            lines=[
                {"account_code": "1100", "debit": Decimal("999"), "credit": Decimal("0")},
                {"account_code": "2100", "debit": Decimal("0"), "credit": Decimal("999")},
            ],
        )
        db.commit()

        tb = AccountingService.get_trial_balance(db)
        assert len(tb) == 0  # Nothing posted


# ── Tests: Feature Flag ──────────────────────────────────────────────


class TestFeatureFlag:
    def test_accounting_disabled_by_default(self):
        # ACCOUNTING_ENABLED reads from env; default is "false"
        assert ACCOUNTING_ENABLED is False

    def test_flag_controls_inventory_service_integration(self, seeded_db):
        """When ACCOUNTING_ENABLED=false, inventory operations should not
        create journal entries. We verify by checking the import value."""
        from backend_core.app.services.inventory_service import ACCOUNTING_ENABLED as inv_flag

        assert inv_flag is False
