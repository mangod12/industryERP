from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .deps import get_db, require_role

router = APIRouter()


@router.post("/", response_model=schemas.InstructionOut, status_code=201)
@router.post("", response_model=schemas.InstructionOut, status_code=201)
def post_instruction(instr_in: schemas.InstructionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss"))):
    instr = models.Instruction(message=instr_in.message, created_by=current_user.id)
    db.add(instr)
    db.flush()

    # Create a global notification for all users
    notif = models.Notification(
        user_id=None,
        role=None,
        message=f"📋 New instruction from Boss: {instr_in.message[:100]}",
        level="info",
        category="instr_from_boss",
        read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(instr)
    return instr


@router.get("/", response_model=List[schemas.InstructionOut])
@router.get("", response_model=List[schemas.InstructionOut])
def list_instructions(db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User"))):
    items = db.query(models.Instruction).order_by(models.Instruction.created_at.desc()).all()
    return items


@router.get("/{instr_id}", response_model=schemas.InstructionOut)
def get_instruction(instr_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User"))):
    instr = db.query(models.Instruction).filter(models.Instruction.id == instr_id).first()
    if not instr:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return instr


@router.put("/{instr_id}", response_model=schemas.InstructionOut)
def update_instruction(instr_id: int, instr_in: schemas.InstructionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss"))):
    instr = db.query(models.Instruction).filter(models.Instruction.id == instr_id).first()
    if not instr:
        raise HTTPException(status_code=404, detail="Instruction not found")
    from datetime import datetime
    instr.message = instr_in.message
    instr.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(instr)
    return instr


@router.delete("/{instr_id}", status_code=204)
def delete_instruction(instr_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss"))):
    instr = db.query(models.Instruction).filter(models.Instruction.id == instr_id).first()
    if not instr:
        raise HTTPException(status_code=404, detail="Instruction not found")
    db.delete(instr)
    db.commit()
    return None
