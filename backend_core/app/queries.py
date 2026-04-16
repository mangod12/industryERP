from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .deps import get_current_user, boss_or_supervisor, get_db

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_query(
    payload: schemas.QueryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = models.Query(
        title=payload.title,
        message=payload.message,
        created_by=current_user.id,
        status="OPEN"
    )

    db.add(query)
    db.flush()

    # Notify Boss about the new query
    notif_boss = models.Notification(
        user_id=None,
        role="Boss",
        message=f"❓ New query from {current_user.username}: {payload.title[:80]}",
        level="info",
        category="query_raised",
        read=False
    )
    db.add(notif_boss)

    # Also notify Software Supervisor
    notif_sup = models.Notification(
        user_id=None,
        role="Software Supervisor",
        message=f"❓ New query from {current_user.username}: {payload.title[:80]}",
        level="info",
        category="query_raised",
        read=False
    )
    db.add(notif_sup)

    db.commit()

    return {"message": "Query submitted successfully", "id": query.id}


@router.get("/me", response_model=List[schemas.QueryResponse])
def my_queries(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(models.Query).filter(
        models.Query.created_by == current_user.id
    ).order_by(models.Query.created_at.desc()).all()


@router.get("/", response_model=List[schemas.QueryResponse])
def all_queries(
    db: Session = Depends(get_db),
    current_user=Depends(boss_or_supervisor)
):
    return db.query(models.Query).order_by(models.Query.created_at.desc()).all()


@router.post("/{query_id}/reply")
def reply_to_query(
    query_id: int,
    payload: schemas.QueryReply,
    db: Session = Depends(get_db),
    current_user=Depends(boss_or_supervisor)
):
    query = db.query(models.Query).filter(
        models.Query.id == query_id
    ).first()

    if not query:
        raise HTTPException(
            status_code=404,
            detail="Query not found"
        )

    if payload.status not in ["IN_PROGRESS", "CLOSED"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be IN_PROGRESS or CLOSED"
        )

    query.admin_reply = payload.reply
    query.status = payload.status

    notification = models.Notification(
        user_id=query.created_by,
        message=f"Your query '{query.title or query.id}' is now {payload.status}",
        level="info",
        category="query_response",
        read=False
    )

    db.add(notification)
    db.commit()

    return {"message": "Query updated successfully"}


@router.delete("/{query_id}", status_code=204)
def delete_query(
    query_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(models.Query).filter(models.Query.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Everyone can only delete their own queries
    if query.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own queries")

    db.delete(query)
    db.commit()
    return None
