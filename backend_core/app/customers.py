from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .deps import get_db, require_role, get_current_user
from .services.customer_service import hard_delete_customer as svc_hard_delete

router = APIRouter()


@router.post("", response_model=schemas.CustomerOut, status_code=201)
def create_customer(customer_in: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cust = models.Customer(name=customer_in.name, project_details=customer_in.project_details)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("", response_model=List[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """List all customers - accessible to all authenticated users"""
    customers = db.query(models.Customer).filter(models.Customer.is_deleted == False).all()
    return customers


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Get a single customer by ID"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, customer_in: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    """Update customer details"""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.name = customer_in.name
    customer.project_details = customer_in.project_details
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, hard: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Delete a customer. By default performs a soft-delete; set `?hard=true` to permanently delete.

    - Soft delete: allowed for Software Supervisor or Boss.
    - Hard delete: allowed only for Boss; will permanently remove customer and related data.
    """
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Hard delete flow
    if hard:
        # Only Boss may hard-delete
        role = getattr(current_user, 'role', '')
        if role != 'Boss':
            raise HTTPException(status_code=403, detail="Not authorized to perform hard delete")

        try:
            svc_hard_delete(db, customer, user=current_user)
            return {"message": "Customer permanently deleted"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hard delete failed: {str(e)}")

    # Soft delete flow (previous behavior)
    role = getattr(current_user, 'role', '')
    if role not in ('Boss', 'Software Supervisor'):
        raise HTTPException(status_code=403, detail="Not authorized to delete customer")

    if customer.is_deleted:
        return {"message": "Customer already deleted"}

    customer.is_deleted = True
    customer.is_active = False
    customer.order_status = "ARCHIVED"
    db.add(customer)

    # Archive associated production items so dashboard and tracking hide them
    try:
        db.query(models.ProductionItem).filter(models.ProductionItem.customer_id == customer_id).update(
            {models.ProductionItem.is_archived: True}, synchronize_session=False
        )
    except Exception:
        # If update fails silently continue with soft-delete
        pass

    db.commit()

    return {"message": "Customer soft-deleted and archived"}





@router.post("/{customer_id}/items", response_model=schemas.ProductionItemOut, status_code=201)
def create_production_item(customer_id: int, item_in: schemas.ProductionItemCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("Boss", "Software Supervisor"))):
    cust = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
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
    cust = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted == False).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    items = db.query(models.ProductionItem).filter(models.ProductionItem.customer_id == customer_id).all()
    return items

@router.post("/query")
def create_query(data: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    message = data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    q = models.Query(
        message=message,
        status="Open"
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"message": "Query submitted", "id": q.id}
@router.get("/query")
def list_queries(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(models.Query).order_by(models.Query.created_at.desc()).all()

@router.post("/queries/{query_id}/close", dependencies=[Depends(require_role("Boss"))])
def close_query(query_id: int, db: Session = Depends(get_db)):
    query = db.query(models.Query).filter(models.Query.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    query.status = "Closed"
    db.commit()
    return {"message": "Query closed successfully"}



