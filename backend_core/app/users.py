from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .deps import get_current_user, get_db
from .security import verify_password, hash_password


router = APIRouter()


@router.get("/me", response_model=schemas.UserResponse)
def read_my_profile(
    current_user: models.User = Depends(get_current_user)
):
    return current_user


@router.put("/me")
def update_my_profile(
    user_in: schemas.UserBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Username & role are NOT editable
    current_user.email = user_in.email
    current_user.company = user_in.company

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully"
    }


@router.post("/me/change-password")
def change_password(
    payload: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not verify_password(
        payload.old_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    current_user.hashed_password = hash_password(
        payload.new_password
    )

    db.commit()

    return {
        "message": "Password changed successfully"
    }
