"""
Dependency helpers: decode JWT, fetch user, attach to request, and role checks.

This module provides `get_db`, `get_current_user`, and role-specific
dependency helpers used by routers. Query endpoints should use
`Depends(get_current_user)` without additional role checks so they remain
open to any authenticated user.
"""

from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .db import SessionLocal
from .security import SECRET_KEY, ALGORITHM, require_roles, verify_password, get_password_hash


# OAuth2 scheme (must match login route)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator:
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if user is None:
        raise credentials_exception

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# Role-based dependencies
def boss_only(
    current_user=Depends(get_current_user)
):
    return require_roles(["Boss"])(current_user)


def supervisor_only(
    current_user=Depends(get_current_user)
):
    return require_roles(["Software Supervisor"])(current_user)


def boss_or_supervisor(
    current_user=Depends(get_current_user)
):
    return require_roles(["Boss", "Software Supervisor"])(current_user)


def require_role(*allowed_roles: str):
    """Backward-compatible wrapper to create a dependency enforcing roles.

    Example usage in routers: Depends(require_role("Boss"))
    """
    def role_dependency(current_user=Depends(get_current_user)):
        return require_roles(list(allowed_roles))(current_user)

    return role_dependency

