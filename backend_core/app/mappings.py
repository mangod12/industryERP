from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .deps import get_db, require_role

router = APIRouter()

@router.get("/", response_model=List[schemas.MaterialMappingOut])
@router.get("", response_model=List[schemas.MaterialMappingOut])
def list_mappings(db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor", "User"))):
    return db.query(models.MaterialMapping).all()

@router.post("/", response_model=schemas.MaterialMappingOut)
@router.post("", response_model=schemas.MaterialMappingOut)
def create_mapping(mapping_in: schemas.MaterialMappingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    # Check if mapping already exists
    existing = db.query(models.MaterialMapping).filter(models.MaterialMapping.excel_name == mapping_in.excel_name).first()
    if existing:
        # Update existing
        existing.material_id = mapping_in.material_id
        db.commit()
        db.refresh(existing)
        return existing
    
    mapping = models.MaterialMapping(**mapping_in.dict())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping

@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    mapping = db.query(models.MaterialMapping).filter(models.MaterialMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(mapping)
    db.commit()
    return {"status": "deleted"}
