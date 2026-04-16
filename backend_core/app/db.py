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


def create_db_and_tables():
    from sqlalchemy import inspect
    from .models import User
    from .security import hash_password
    
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
            print(f"[backend_core] ⚠️  Admin user created — username: admin / password: {_admin_pw}")
            print("[backend_core] ⚠️  SAVE THIS PASSWORD. It will NOT be shown again.")
    except Exception as e:
        print(f"[backend_core] Error seeding admin user: {e}")
    finally:
        db.close()
