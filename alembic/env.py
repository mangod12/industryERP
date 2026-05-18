"""
Alembic environment configuration for KBSteel ERP.

Imports ALL model generations (v1, v2, v3) so that Base.metadata
contains every table definition for autogenerate support.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `backend_core.app.*`
# imports resolve correctly regardless of where alembic is invoked from.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import ALL models so Base.metadata is fully populated.
# Order matters: db.py defines Base, then each model module registers tables.
# ---------------------------------------------------------------------------
from backend_core.app.db import Base, DATABASE_URL  # noqa: E402
import backend_core.app.models as _models_v1        # noqa: E402, F401
import backend_core.app.models_v2 as _models_v2     # noqa: E402, F401
import backend_core.app.models_v3 as _models_v3     # noqa: E402, F401
import backend_core.app.models_accounting as _models_acct  # noqa: E402, F401

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override sqlalchemy.url with DATABASE_URL env var when available.
# This ensures production migrations use the correct database.
# ---------------------------------------------------------------------------
effective_url = os.getenv("DATABASE_URL", None) or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", effective_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
