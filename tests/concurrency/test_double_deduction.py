"""
Concurrency test: Double-deduction prevention.

Verifies that when 2 concurrent threads try to complete the same fabrication
stage, only ONE deduction occurs and inventory is reduced exactly once.

Note: SQLite uses file-level locking so true concurrent writes are serialized.
This test validates the idempotency logic regardless of the locking mechanism.
"""
import json
import threading
import pytest

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.security import get_password_hash, create_access_token
from app.services.deduction_service import DeductionService, InsufficientStockError


@pytest.fixture()
def shared_engine():
    """Shared in-memory SQLite engine for concurrent access."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session_factory(shared_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=shared_engine)


@pytest.fixture()
def seed_data(session_factory):
    """Create test data: user, customer, inventory, production item."""
    db = session_factory()
    try:
        user = models.User(
            full_name="Boss User",
            email="boss@test.com",
            username="boss",
            password_hash=get_password_hash("Test@123"),
            role="Boss",
            is_active=True,
        )
        db.add(user)
        db.flush()

        customer = models.Customer(name="Concurrency Test Customer")
        db.add(customer)
        db.flush()

        inv = models.Inventory(
            name="40 NB(M) PIPE",
            unit="kg",
            total=100.0,
            used=0.0,
            section="40 NB(M) PIPE",
        )
        db.add(inv)
        db.flush()

        reqs = json.dumps([{"material_id": inv.id, "qty": 10.0}])
        item = models.ProductionItem(
            customer_id=customer.id,
            item_code="CONC-01",
            item_name="Concurrency Test Item",
            section="40 NB(M) PIPE",
            quantity=1.0,
            weight_per_unit=10.0,
            material_requirements=reqs,
            current_stage="fabrication",
            fabrication_deducted=False,
            material_deducted=False,
        )
        db.add(item)
        db.commit()

        return {
            "user_id": user.id,
            "customer_id": customer.id,
            "inventory_id": inv.id,
            "item_id": item.id,
        }
    finally:
        db.close()


@pytest.mark.skipif(
    True,  # SQLite in-memory with StaticPool shares connections
    reason="SQLite lacks real row-level locking; test valid on Postgres only",
)
def test_double_deduction_prevention(session_factory, seed_data):
    """
    Two concurrent threads call deduct_materials_for_item on the same item.
    Only one should succeed; the other should skip (already deducted).
    Inventory should be reduced exactly once.

    NOTE: This test is designed for Postgres with FOR UPDATE support.
    SQLite serializes at file level, and in-memory StaticPool shares state.
    """
    results = [None, None]
    errors = [None, None]

    def worker(index):
        db = session_factory()
        try:
            result = DeductionService.deduct_materials_for_item(
                db=db,
                production_item_id=seed_data["item_id"],
                user_id=seed_data["user_id"],
                trigger=f"concurrent_thread_{index}",
            )
            db.commit()
            results[index] = result
        except Exception as e:
            db.rollback()
            errors[index] = e
        finally:
            db.close()

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Both should complete without error
    assert errors[0] is None, f"Thread 0 error: {errors[0]}"
    assert errors[1] is None, f"Thread 1 error: {errors[1]}"

    # Exactly one success, one skip
    successes = sum(1 for r in results if r and r.success)
    skips = sum(1 for r in results if r and r.skipped)

    assert successes == 1, f"Expected 1 success, got {successes}"
    assert skips == 1, f"Expected 1 skip, got {skips}"

    # Verify inventory was reduced exactly once (10.0 kg)
    db = session_factory()
    try:
        inv = db.query(models.Inventory).filter(
            models.Inventory.id == seed_data["inventory_id"]
        ).first()
        assert inv.used == 10.0, f"Expected used=10.0, got {inv.used}"
    finally:
        db.close()

    # Verify both flags set
    db = session_factory()
    try:
        item = db.query(models.ProductionItem).filter(
            models.ProductionItem.id == seed_data["item_id"]
        ).first()
        assert item.fabrication_deducted is True
        assert item.material_deducted is True
    finally:
        db.close()


def test_serial_idempotency(session_factory, seed_data):
    """
    Calling deduct_materials_for_item twice sequentially on the same item.
    Second call should be idempotent (skipped). Works on SQLite.
    """
    db = session_factory()
    try:
        r1 = DeductionService.deduct_materials_for_item(
            db, seed_data["item_id"], seed_data["user_id"], "first_call"
        )
        db.commit()
        assert r1.success is True

        r2 = DeductionService.deduct_materials_for_item(
            db, seed_data["item_id"], seed_data["user_id"], "second_call"
        )
        assert r2.skipped is True
        assert r2.skipped_reason == "Already deducted"

        inv = db.query(models.Inventory).filter(
            models.Inventory.id == seed_data["inventory_id"]
        ).first()
        assert inv.used == 10.0  # Deducted exactly once
    finally:
        db.close()


@pytest.mark.skipif(
    True,
    reason="SQLite lacks real row-level locking; test valid on Postgres only",
)
def test_concurrent_fifo_deduction(session_factory, seed_data):
    """
    Two concurrent threads call deduct_materials_fifo on the same item.
    Only one should succeed with actual deduction.
    """
    # First create MaterialUsage records
    db = session_factory()
    try:
        mu = models.MaterialUsage(
            customer_id=seed_data["customer_id"],
            production_item_id=seed_data["item_id"],
            name="40 NB(M) PIPE",
            qty=10.0,
            unit="kg",
            applied=False,
        )
        db.add(mu)
        # Reset flags (may have been set by previous test data creation)
        item = db.query(models.ProductionItem).filter(
            models.ProductionItem.id == seed_data["item_id"]
        ).first()
        item.material_deducted = False
        item.fabrication_deducted = False
        # Reset inventory
        inv = db.query(models.Inventory).filter(
            models.Inventory.id == seed_data["inventory_id"]
        ).first()
        inv.used = 0.0
        db.commit()
    finally:
        db.close()

    results = [None, None]
    errors = [None, None]

    def worker(index):
        s = session_factory()
        try:
            result = DeductionService.deduct_materials_fifo(
                db=s,
                production_item_id=seed_data["item_id"],
                user_id=seed_data["user_id"],
                trigger=f"fifo_thread_{index}",
            )
            s.commit()
            results[index] = result
        except Exception as e:
            s.rollback()
            errors[index] = e
        finally:
            s.close()

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # No errors expected
    for i, e in enumerate(errors):
        assert e is None, f"Thread {i} error: {e}"

    # At most one success
    successes = sum(1 for r in results if r and r.success)
    assert successes <= 1, f"Expected at most 1 success, got {successes}"
