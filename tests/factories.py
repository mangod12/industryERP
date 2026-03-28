"""
KBSteel ERP — Test Data Factories
===================================
Helper functions to create test data for various models.
All factories take a db session and return committed ORM objects.
"""
import json
from datetime import datetime
from decimal import Decimal

from app import models
from app.models_bom import Assembly, AssemblyPart, AssemblyStageTracking


def create_customer(db, name="Test Customer", project_details="Test Project"):
    """Create a test customer."""
    customer = models.Customer(
        name=name,
        project_details=project_details,
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_inventory_item(
    db,
    name="40 NB(M) PIPE",
    unit="kg",
    total=1000.0,
    used=0.0,
    section=None,
    category=None,
):
    """Create a test inventory item."""
    item = models.Inventory(
        name=name,
        unit=unit,
        total=total,
        used=used,
        section=section or name,
        category=category,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_production_item(
    db,
    customer_id,
    item_code="HR110-01",
    item_name="Top Rail",
    section="40 NB(M) PIPE",
    length_mm=868,
    quantity=1.0,
    weight_per_unit=3.09,
    material_requirements=None,
    current_stage="fabrication",
):
    """Create a test production item."""
    item = models.ProductionItem(
        customer_id=customer_id,
        item_code=item_code,
        item_name=item_name,
        section=section,
        length_mm=length_mm,
        quantity=quantity,
        weight_per_unit=weight_per_unit,
        material_requirements=material_requirements,
        current_stage=current_stage,
        fabrication_deducted=False,
        material_deducted=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_material_usage(
    db,
    customer_id,
    production_item_id,
    name="40 NB(M) PIPE",
    qty=3.09,
    unit="kg",
    applied=False,
):
    """Create a material usage record (pending deduction)."""
    mu = models.MaterialUsage(
        customer_id=customer_id,
        production_item_id=production_item_id,
        name=name,
        qty=qty,
        unit=unit,
        applied=applied,
    )
    db.add(mu)
    db.commit()
    db.refresh(mu)
    return mu


def create_stage_tracking(
    db,
    production_item_id,
    stage="fabrication",
    status="in_progress",
    is_checked=False,
):
    """Create a stage tracking record."""
    st = models.StageTracking(
        production_item_id=production_item_id,
        stage=stage,
        status=status,
        started_at=datetime.utcnow() if status == "in_progress" else None,
        is_checked=is_checked,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


def create_production_item_with_materials(
    db,
    customer_id,
    inventory_id,
    item_code="HR110-01",
    item_name="Top Rail",
    section="40 NB(M) PIPE",
    quantity=1.0,
    weight_per_unit=3.09,
):
    """Create a production item with material requirements JSON linking to an inventory item."""
    reqs = json.dumps([{"material_id": inventory_id, "qty": quantity * weight_per_unit}])
    item = create_production_item(
        db,
        customer_id=customer_id,
        item_code=item_code,
        item_name=item_name,
        section=section,
        quantity=quantity,
        weight_per_unit=weight_per_unit,
        material_requirements=reqs,
    )
    return item


# ---------------------------------------------------------------------------
# BOM (Bill of Materials) Factories
# ---------------------------------------------------------------------------


def create_assembly(
    db,
    customer_id,
    assembly_code="HR110",
    assembly_name="Handrail Type A",
    lot_number="LOT-03",
    ordered_qty=1,
):
    """Create a test assembly with stage tracking rows for all 3 stages."""
    assembly = Assembly(
        customer_id=customer_id,
        assembly_code=assembly_code,
        assembly_name=assembly_name,
        lot_number=lot_number,
        ordered_qty=ordered_qty,
    )
    db.add(assembly)
    db.flush()

    for stage in ["fabrication", "painting", "dispatch"]:
        st = AssemblyStageTracking(
            assembly_id=assembly.id,
            stage=stage,
            total_pieces=0,
        )
        db.add(st)

    db.commit()
    db.refresh(assembly)
    return assembly


def create_assembly_part(
    db,
    assembly_id,
    mark_number="HR110-01",
    part_name="Top Rail",
    section="40 NB(M) PIPE",
    total_qty=1,
    weight_per_unit_kg=3.09,
):
    """Create a test assembly part and return it."""
    part = AssemblyPart(
        assembly_id=assembly_id,
        mark_number=mark_number,
        part_name=part_name,
        section=section,
        total_qty=total_qty,
        weight_per_unit_kg=Decimal(str(weight_per_unit_kg)),
        total_weight_kg=Decimal(str(weight_per_unit_kg * total_qty)),
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part
