"""
KBSteel ERP — Test Configuration & Fixtures
=============================================
Provides fresh in-memory SQLite database per test, TestClient, and auth token
fixtures for all 6 roles.
"""
import sys
import os
import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add backend_core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_core"))

from app.db import Base
from app.main import create_app
from app.deps import get_db
from app import models, models_v2, models_bom
from app.security import get_password_hash, create_access_token


@pytest.fixture()
def db_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all v1 + v2 tables
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Create a fresh database session per test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(db_engine):
    """Create a FastAPI app with test database override."""
    application = create_app()

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = override_get_db
    # Also override the security module's get_db if it exists
    from app.security import get_db as security_get_db
    application.dependency_overrides[security_get_db] = override_get_db

    return application


@pytest.fixture()
def client(app):
    """Test client for making HTTP requests."""
    return TestClient(app)


def _create_user(db_session, role: str, username: str = None, email: str = None):
    """Helper to create a user in the test database."""
    if username is None:
        username = f"test_{role.lower().replace(' ', '_')}"
    if email is None:
        email = f"{username}@test.com"
    user = models.User(
        full_name=f"Test {role}",
        email=email,
        username=username,
        password_hash=get_password_hash("Test@123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_token(user):
    """Create a JWT token for a test user."""
    return create_access_token(
        data={"sub": user.username, "role": user.role}
    )


def _auth_header(token: str) -> dict:
    """Create Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def boss_user(db_session):
    return _create_user(db_session, "Boss")


@pytest.fixture()
def supervisor_user(db_session):
    return _create_user(db_session, "Software Supervisor")


@pytest.fixture()
def storekeeper_user(db_session):
    return _create_user(db_session, "Store Keeper")


@pytest.fixture()
def qa_user(db_session):
    return _create_user(db_session, "QA Inspector")


@pytest.fixture()
def dispatch_user(db_session):
    return _create_user(db_session, "Dispatch Operator")


@pytest.fixture()
def readonly_user(db_session):
    return _create_user(db_session, "User")


@pytest.fixture()
def boss_token(boss_user):
    return _make_token(boss_user)


@pytest.fixture()
def supervisor_token(supervisor_user):
    return _make_token(supervisor_user)


@pytest.fixture()
def storekeeper_token(storekeeper_user):
    return _make_token(storekeeper_user)


@pytest.fixture()
def qa_token(qa_user):
    return _make_token(qa_user)


@pytest.fixture()
def dispatch_token(dispatch_user):
    return _make_token(dispatch_user)


@pytest.fixture()
def readonly_token(readonly_user):
    return _make_token(readonly_user)


@pytest.fixture()
def boss_headers(boss_token):
    return _auth_header(boss_token)


@pytest.fixture()
def supervisor_headers(supervisor_token):
    return _auth_header(supervisor_token)


@pytest.fixture()
def storekeeper_headers(storekeeper_token):
    return _auth_header(storekeeper_token)


@pytest.fixture()
def qa_headers(qa_token):
    return _auth_header(qa_token)


@pytest.fixture()
def dispatch_headers(dispatch_token):
    return _auth_header(dispatch_token)


@pytest.fixture()
def readonly_headers(readonly_token):
    return _auth_header(readonly_token)
