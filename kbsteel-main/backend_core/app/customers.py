from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .deps import get_db, require_role, get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=schemas.CustomerOut, status_code=201)
def create_customer(customer_in: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    cust = models.Customer(name=customer_in.name, project_details=customer_in.project_details)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("", response_model=List[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """List all customers - accessible to all authenticated users"""
    customers = db.query(models.Customer).all()
    return customers


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Get a single customer by ID"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, customer_in: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    """Update customer details"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.name = customer_in.name
    customer.project_details = customer_in.project_details
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    """Delete a customer and all their production items"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Delete related production items and their stages
    for item in customer.production_items:
        db.query(models.StageTracking).filter(models.StageTracking.production_item_id == item.id).delete()
        db.delete(item)
    
    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted"}


@router.post("/{customer_id}/items", response_model=schemas.ProductionItemOut, status_code=201)
def create_production_item(customer_id: int, item_in: schemas.ProductionItemCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    cust = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    item = models.ProductionItem(
        customer_id=customer_id, 
        item_code=item_in.item_code, 
        item_name=item_in.item_name, 
        section=item_in.section, 
        length_mm=item_in.length_mm,
        quantity=item_in.quantity,
        unit=item_in.unit,
        weight_per_unit=item_in.weight_per_unit,
        material_requirements=item_in.material_requirements,
        checklist=item_in.checklist,
        notes=item_in.notes,
        fabrication_deducted=False,
    )
    db.add(item)
    db.flush()
    
    # Initialize at Fabrication stage
    from datetime import datetime
    stage = models.StageTracking(
        production_item_id=item.id,
        stage="fabrication",
        status="pending",
        updated_by=current_user.id,
    )
    db.add(stage)
    
    db.commit()
    db.refresh(item)
    return item


@router.get("/{customer_id}/items", response_model=List[schemas.ProductionItemOut])
def list_production_items(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """List all production items for a customer"""
    items = db.query(models.ProductionItem).filter(models.ProductionItem.customer_id == customer_id).all()
    return items
