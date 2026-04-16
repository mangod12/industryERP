from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from .deps import get_db, boss_or_supervisor
from . import models, schemas
from .security import verify_password, hash_password, create_access_token, RateLimiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle both JSON body and form-encoded (OAuth2) logins.

    Returns a token dict matching `schemas.Token`.
    """
    # --- Rate Limiting ---
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining = RateLimiter.check_rate_limit(f"login:{client_ip}", max_attempts=5, window_seconds=300)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 5 minutes."
        )

    ctype = (request.headers.get("content-type") or "").lower()

    if "application/json" in ctype:
        body = await request.json()
        try:
            form = schemas.LoginRequest(**body)
            username = form.username
            password = form.password
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
    else:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username and password required")

    try:
        user = db.query(models.User).filter(models.User.username == username).first()

        if not user or not getattr(user, "hashed_password", None):
            RateLimiter.record_attempt(f"login:{client_ip}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        if not verify_password(password, user.hashed_password):
            RateLimiter.record_attempt(f"login:{client_ip}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

        access_token = create_access_token(data={"sub": user.username, "role": user.role})

        response = {"access_token": access_token, "token_type": "bearer", "role": user.role}
        logger.info(f"Successful login for user: {username}")
        return response
    except HTTPException:
        # Re-raise known HTTP errors unchanged
        raise
    except Exception as e:
        import traceback
        logger.error(f"Unexpected login error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db), current_user=Depends(boss_or_supervisor)):
    """Supervisor OR Boss only user registration. Attempts ORM insert but returns a clear error if DB schema mismatches.
    """
    # Prevent duplicate username/email
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    if len(user_in.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    # Normalize role to Title Case for backend permission consistency
    # Frontend might send 'software_supervisor' -> we want 'Software Supervisor'
    role_map = {
        "boss": "Boss",
        "software_supervisor": "Software Supervisor", 
        "user": "User",
        "store_keeper": "Store Keeper",
        "qa_inspector": "QA Inspector",
        "dispatch_operator": "Dispatch Operator",
        "fabricator": "Fabricator",
        "painter": "Painter",
        "dispatch": "Dispatch"
    }
    
    # 1. Try exact match first (if they sent "Boss")
    # 2. Try lower case lookup (if they sent "boss")
    # 3. Default to "User" if unknown
    final_role = user_in.role
    if user_in.role in role_map.values():
        final_role = user_in.role # Already correct
    else:
        final_role = role_map.get(user_in.role.lower(), "User")

    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=final_role,
        company=getattr(user_in, "company", None),
        is_active=True,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except OperationalError as e:
        # Likely DB schema mismatch (missing column). Surface a clear error.
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during user creation: {e}")

    return {"message": "User created successfully", "username": new_user.username, "role": new_user.role}
