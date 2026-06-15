"""Create the first production admin user when bootstrap env vars are present.

This script is intentionally idempotent so it can run on every container start.
It creates a Boss user only when ADMIN_PASSWORD is set and the username does not
already exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_core.app import models  # noqa: E402
from backend_core.app.db import SessionLocal  # noqa: E402
from backend_core.app.security import hash_password  # noqa: E402


def main() -> int:
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        print("[bootstrap] ADMIN_PASSWORD not set; skipping admin bootstrap.")
        return 0

    if len(password) < 12:
        raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters for production bootstrap.")

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@kbsteel.local")
    role = os.getenv("ADMIN_ROLE", "Boss")
    company = os.getenv("ADMIN_COMPANY", "Kumar Brothers Steel")

    with SessionLocal() as db:
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            print(f"[bootstrap] Admin user '{username}' already exists; leaving password unchanged.")
            return 0

        user = models.User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            company=company,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"[bootstrap] Created admin user '{username}' with role '{role}'.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
