"""
Pytest configuration and shared fixtures for KBSteel ERP tests.

Provides:
- In-memory SQLite test database with all v1/v2/v3 tables
- FastAPI TestClient with dependency overrides for DB and auth
- Per-role authenticated client fixtures (boss, storekeeper, qa, dispatch, user)
- Factory functions for creating test data (User, Customer, ProductionItem, Inventory, StockLot)
"""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Ensure the backend package is importable regardless of working directory
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend_core.app import (
    models_accounting,  # noqa: F401 — register accounting tables
    models_v3,  # noqa: F401 — register v3 tables on BaseV1
)
from backend_core.app.db import Base as BaseV1
from backend_core.app.deps import (
    get_current_user as deps_get_current_user,
)
from backend_core.app.deps import (
    get_db as deps_get_db,
)
from backend_core.app.models import (
    Customer,
    Inventory,
    ProductionItem,
    User,
)
from backend_core.app.models_v2 import Base as BaseV2
from backend_core.app.models_v2 import (
    MaterialMaster,
    MaterialType,
    QAStatus,
    StockLot,
    Vendor,
)
from backend_core.app.security import (
    get_current_user as security_get_current_user,
)
from backend_core.app.security import (
    get_db as security_get_db,
)
from backend_core.app.security import (
    hash_password,
)

# ===========================================================================
# Database fixtures
# ===========================================================================

SQLALCHEMY_TEST_URL = "sqlite://"  # in-memory


@pytest.fixture(scope="function")
def engine():
    """Create a fresh in-memory SQLite engine per test."""
    eng = create_engine(
        SQLALCHEMY_TEST_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable WAL-like behaviour and foreign keys for SQLite
    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create ALL tables (v1 + v2 + v3 share the same MetaData when on BaseV1,
    # but v2 has its own Base — create both)
    BaseV1.metadata.create_all(bind=eng)
    BaseV2.metadata.create_all(bind=eng)

    yield eng

    BaseV2.metadata.drop_all(bind=eng)
    BaseV1.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def db(engine):
    """Provide a transactional database session that rolls back after each test."""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()

    yield session

    session.rollback()
    session.close()


# ===========================================================================
# Factory functions
# ===========================================================================

_user_counter = 0


def create_test_user(
    db: Session,
    *,
    role: str = "Boss",
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: str = "TestPass1!",
    is_active: bool = True,
    **overrides,
) -> User:
    """Create and persist a User with sensible defaults."""
    global _user_counter
    _user_counter += 1
    suffix = _user_counter

    user = User(
        username=username or f"testuser_{suffix}",
        email=email or f"testuser_{suffix}@example.com",
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
        company=overrides.pop("company", "Test Steel Co"),
        **overrides,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_customer(
    db: Session,
    *,
    name: Optional[str] = None,
    **overrides,
) -> Customer:
    """Create and persist a Customer."""
    global _user_counter
    _user_counter += 1
    suffix = _user_counter

    customer = Customer(
        name=name or f"Test Customer {suffix}",
        project_details=overrides.pop("project_details", "Test project"),
        email=overrides.pop("email", f"customer_{suffix}@example.com"),
        phone=overrides.pop("phone", "9876543210"),
        is_active=overrides.pop("is_active", True),
        order_status=overrides.pop("order_status", "ACTIVE"),
        is_deleted=overrides.pop("is_deleted", False),
        **overrides,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_test_production_item(
    db: Session,
    customer_id: int,
    *,
    item_code: Optional[str] = None,
    item_name: Optional[str] = None,
    **overrides,
) -> ProductionItem:
    """Create and persist a ProductionItem linked to a customer."""
    global _user_counter
    _user_counter += 1
    suffix = _user_counter

    item = ProductionItem(
        customer_id=customer_id,
        item_code=item_code or f"ITM-{suffix:04d}",
        item_name=item_name or f"Test Item {suffix}",
        section=overrides.pop("section", "ISMC 200"),
        length_mm=overrides.pop("length_mm", 6000),
        quantity=overrides.pop("quantity", 1.0),
        current_stage=overrides.pop("current_stage", "fabrication"),
        **overrides,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_test_inventory(
    db: Session,
    *,
    name: Optional[str] = None,
    **overrides,
) -> Inventory:
    """Create and persist an Inventory row."""
    global _user_counter
    _user_counter += 1
    suffix = _user_counter

    inv = Inventory(
        name=name or f"Steel Plate {suffix}",
        unit=overrides.pop("unit", "kg"),
        total=overrides.pop("total", 1000.0),
        used=overrides.pop("used", 0.0),
        code=overrides.pop("code", f"SP-{suffix:04d}"),
        section=overrides.pop("section", None),
        category=overrides.pop("category", "plate"),
        **overrides,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def create_test_stock_lot(
    db: Session,
    *,
    material_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    **overrides,
) -> StockLot:
    """Create and persist a v2 StockLot.

    If *material_id* is not supplied, a MaterialMaster row is created first.
    If *vendor_id* is not supplied, a Vendor row is created first.
    """
    global _user_counter
    _user_counter += 1
    suffix = _user_counter

    if material_id is None:
        mat = MaterialMaster(
            code=f"MAT-{suffix:04d}",
            name=f"Test Material {suffix}",
            material_type=MaterialType.PLATE,
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)
        material_id = mat.id

    if vendor_id is None:
        vendor = Vendor(
            code=f"V-{suffix:04d}",
            name=f"Test Vendor {suffix}",
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        vendor_id = vendor.id

    net = overrides.pop("net_weight_kg", Decimal("500.000"))
    gross = overrides.pop("gross_weight_kg", net + Decimal("10.000"))
    current = overrides.pop("current_weight_kg", net)

    lot = StockLot(
        lot_number=overrides.pop("lot_number", f"LOT-{suffix:06d}"),
        material_id=material_id,
        vendor_id=vendor_id,
        gross_weight_kg=gross,
        tare_weight_kg=overrides.pop("tare_weight_kg", Decimal("10.000")),
        net_weight_kg=net,
        current_weight_kg=current,
        received_date=overrides.pop("received_date", datetime.utcnow()),
        qa_status=overrides.pop("qa_status", QAStatus.APPROVED),
        **overrides,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


# ===========================================================================
# FastAPI TestClient fixtures
# ===========================================================================


def _make_client(db: Session, user: User):
    """Build a TestClient with DB and auth overrides for *user*."""
    from backend_core.app.main import create_app

    app = create_app()

    # Override database dependency
    def _override_get_db():
        yield db

    # Override auth dependency — return the given user directly
    async def _override_get_current_user():
        return user

    # Override both security.py and deps.py versions (routers import from either)
    app.dependency_overrides[security_get_db] = _override_get_db
    app.dependency_overrides[deps_get_db] = _override_get_db
    app.dependency_overrides[security_get_current_user] = _override_get_current_user
    app.dependency_overrides[deps_get_current_user] = _override_get_current_user

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client(db):
    """Unauthenticated TestClient (no auth override, but DB is overridden)."""
    from backend_core.app.main import create_app

    app = create_app()

    def _override_get_db():
        yield db

    # Override both security.py and deps.py versions
    app.dependency_overrides[security_get_db] = _override_get_db
    app.dependency_overrides[deps_get_db] = _override_get_db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def boss_client(db):
    """TestClient authenticated as a Boss user."""
    user = create_test_user(db, role="Boss", username="boss_test")
    return _make_client(db, user)


@pytest.fixture()
def storekeeper_client(db):
    """TestClient authenticated as a Store Keeper."""
    user = create_test_user(db, role="Store Keeper", username="storekeeper_test")
    return _make_client(db, user)


@pytest.fixture()
def qa_client(db):
    """TestClient authenticated as a QA Inspector."""
    user = create_test_user(db, role="QA Inspector", username="qa_test")
    return _make_client(db, user)


@pytest.fixture()
def dispatch_client(db):
    """TestClient authenticated as a Dispatch Operator."""
    user = create_test_user(db, role="Dispatch Operator", username="dispatch_test")
    return _make_client(db, user)


@pytest.fixture()
def user_client(db):
    """TestClient authenticated as a basic User."""
    user = create_test_user(db, role="User", username="user_test")
    return _make_client(db, user)
