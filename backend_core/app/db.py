import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Prefer explicit DATABASE_URL env var. If not provided, fall back to local
# SQLite for development only. In production, always set DATABASE_URL.
env_db = os.getenv("DATABASE_URL")
env_mode = os.getenv("ENVIRONMENT", "development")

if env_db:
    DATABASE_URL = env_db
elif env_mode == "production":
    raise RuntimeError(
        "CRITICAL: DATABASE_URL environment variable must be set in production! "
        "Example: DATABASE_URL=postgresql://user:pass@host/dbname"
    )
else:
    # Development fallback — local SQLite
    _data_dir = Path(__file__).resolve().parent.parent / "data"
    _data_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{_data_dir / 'kbsteel_dev.db'}"

# Log without exposing credentials
_masked = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
print(f"[backend_core] Database: ...@{_masked}")

# Use echo=False in production; set echo=True for debugging
# Use echo=False in production; set echo=True for debugging
# Postgres does not need check_same_thread
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _run_migrations():
    """Run safe schema migrations for PostgreSQL.

    Handles column renames and additions that create_all() cannot do
    on existing tables. Each migration is idempotent.
    """
    from sqlalchemy import text, inspect as sa_inspect

    if DATABASE_URL.startswith("sqlite"):
        return  # SQLite dev DB is recreated from scratch

    inspector = sa_inspect(engine)
    tables = set(inspector.get_table_names())

    def _cols(table):
        if table not in tables:
            return set()
        return {c["name"] for c in inspector.get_columns(table)}

    def _add(conn, table, col, definition):
        print(f"[migration] Adding {table}.{col}")
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {definition}"))

    with engine.begin() as conn:
        # --- users ---
        cols = _cols("users")
        if cols:
            if "password_hash" in cols and "hashed_password" not in cols:
                print("[migration] Renaming users.password_hash → hashed_password")
                conn.execute(text('ALTER TABLE users RENAME COLUMN password_hash TO hashed_password'))
            elif "password" in cols and "hashed_password" not in cols:
                print("[migration] Renaming users.password → hashed_password")
                conn.execute(text('ALTER TABLE users RENAME COLUMN password TO hashed_password'))
            if "is_active" not in cols:
                _add(conn, "users", "is_active", "BOOLEAN DEFAULT TRUE")
            if "company" not in cols:
                _add(conn, "users", "company", "VARCHAR")
            if "created_at" not in cols:
                _add(conn, "users", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

        # --- customers ---
        cols = _cols("customers")
        if cols:
            if "order_status" not in cols:
                _add(conn, "customers", "order_status", "VARCHAR DEFAULT 'ACTIVE'")
            if "is_deleted" not in cols:
                _add(conn, "customers", "is_deleted", "BOOLEAN DEFAULT FALSE")

        # --- production_items ---
        cols = _cols("production_items")
        if cols:
            if "is_completed" not in cols:
                _add(conn, "production_items", "is_completed", "BOOLEAN DEFAULT FALSE")

        # --- notifications ---
        cols = _cols("notifications")
        if cols:
            if "category" not in cols:
                _add(conn, "notifications", "category", "VARCHAR")

        # --- queries ---
        cols = _cols("queries")
        if cols:
            if "title" not in cols:
                _add(conn, "queries", "title", "VARCHAR")
            if "message" not in cols:
                _add(conn, "queries", "message", "TEXT")
            if "admin_reply" not in cols:
                _add(conn, "queries", "admin_reply", "TEXT")


def create_db_and_tables():
    from sqlalchemy import inspect
    from .models import User
    from .security import hash_password

    # Run migrations BEFORE create_all so column renames happen first
    _run_migrations()

    Base.metadata.create_all(bind=engine)

    # Check if we need to seed the admin user
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            import secrets as _secrets
            _admin_pw = _secrets.token_urlsafe(16)  # Strong random password
            print("[backend_core] Seeding default admin user...")
            admin_user = User(
                username="admin",
                email="admin@kbsteel.com",
                hashed_password=hash_password(_admin_pw),
                role="Boss",
                company="Kumar Brothers Steel"
            )
            db.add(admin_user)
            db.commit()
            print(f"[backend_core] Admin user created — username: admin / password: {_admin_pw}")
            print("[backend_core] SAVE THIS PASSWORD. It will NOT be shown again.")
    except Exception as e:
        print(f"[backend_core] Error seeding admin user: {e}")
    finally:
        db.close()
