"""Seed deterministic demo data for local QA and Playwright runs.

Usage:
    python scripts/seed_demo.py

Optional environment:
    DATABASE_URL=sqlite:///path/to/demo.db
    DEMO_ADMIN_PASSWORD=Boss1234!  # pragma: allowlist secret
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_core.app import models, models_accounting, models_v2, models_v3  # noqa: E402,F401
from backend_core.app.db import Base, SessionLocal, engine  # noqa: E402
from backend_core.app.security import hash_password  # noqa: E402

DEMO_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "Boss1234!")  # pragma: allowlist secret


def get_or_create(db, model, defaults=None, **lookup):
    obj = db.query(model).filter_by(**lookup).first()
    defaults = defaults or {}
    if obj is None:
        obj = model(**lookup, **defaults)
        db.add(obj)
        db.flush()
        return obj
    for key, value in defaults.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def seed_users(db):
    users = [
        ("admin", "admin@kbsteel.local", "Boss", "Kumar Brothers Steel Pvt Ltd"),
        ("boss", "boss@kbsteel.local", "Boss", "Kumar Brothers Steel Pvt Ltd"),
        ("store", "store@kbsteel.local", "Store Keeper", "Kumar Brothers Steel Pvt Ltd"),
        ("qa", "qa@kbsteel.local", "QA Inspector", "Kumar Brothers Steel Pvt Ltd"),
        ("dispatch", "dispatch@kbsteel.local", "Dispatch Operator", "Kumar Brothers Steel Pvt Ltd"),
    ]
    created = {}
    for username, email, role, company in users:
        created[username] = get_or_create(
            db,
            models.User,
            username=username,
            defaults={
                "email": email,
                "hashed_password": hash_password(DEMO_PASSWORD),
                "role": role,
                "company": company,
                "is_active": True,
            },
        )
    return created


def seed_company_settings(db, admin_id):
    settings = {
        "company_name": "Kumar Brothers Steel Pvt Ltd",
        "company_address": "Industrial Area, Bokaro Steel City, Jharkhand",
        "company_gstin": "20ABCDE1234F1Z5",
        "company_phone": "+91-6542-240-118",
        "company_email": "operations@kbsteel.local",
        "company_logo_url": "",
        "dispatch_requires_weighbridge": "true",
        "qa_hold_requires_boss_override": "true",
        "stock_valuation_method": "FIFO",
    }
    for key, value in settings.items():
        get_or_create(
            db,
            models_v2.SystemConfig,
            key=key,
            defaults={
                "value": value,
                "description": f"Demo setting: {key}",
                "updated_by": admin_id,
            },
        )

    sequences = [
        ("grn", "GRN", 17, 2026, 5, "{prefix}/{fy}/{####}"),
        ("dispatch", "DSP", 9, 2026, 5, "{prefix}/{fy}/{####}"),
        ("lot", "LOT", 44, 2026, 5, "{prefix}-{####}"),
        ("movement", "MOV", 88, 2026, 5, "{prefix}-{fy}-{####}"),
        ("journal", "JV", 4, 2026, 5, "{prefix}/{fy}/{####}"),
    ]
    for sequence_name, prefix, current_number, year, padding, format_str in sequences:
        get_or_create(
            db,
            models_v2.NumberSequence,
            sequence_name=sequence_name,
            defaults={
                "prefix": prefix,
                "current_number": current_number,
                "year": year,
                "padding": padding,
                "format_str": format_str,
            },
        )


def seed_legacy_operations(db, users):
    customer = get_or_create(
        db,
        models.Customer,
        name="Metro Rail Depot Expansion",
        defaults={
            "project_details": "Fabrication package for platform trusses and mezzanine support steel.",
            "email": "projects@metro.example",
            "phone": "+91-98765-11001",
            "is_active": True,
            "order_status": "ACTIVE",
            "is_deleted": False,
        },
    )
    get_or_create(
        db,
        models.Customer,
        name="Blue Ridge Warehouse",
        defaults={
            "project_details": "Warehouse shed frame, purlins, and dispatch-ready secondary members.",
            "email": "procurement@blueridge.example",
            "phone": "+91-98765-22002",
            "is_active": True,
            "order_status": "ACTIVE",
            "is_deleted": False,
        },
    )

    inventory_rows = [
        ("ISMB 200 Beam", "kg", 12500.0, 2860.0, "STL-ISMB-200", "ISMB 200", "Structural"),
        ("MS Plate 10mm", "kg", 8400.0, 1325.0, "STL-PLT-010", "Plate 10mm", "Plate"),
        ("Paint Primer Red Oxide", "ltr", 640.0, 180.0, "CHEM-PRIMER-RO", "Primer", "Consumable"),
        ("Welding Rod E7018", "kg", 950.0, 215.0, "CONS-E7018", "Welding Rod", "Consumable"),
    ]
    legacy_inventory = {}
    for name, unit, total, used, code, section, category in inventory_rows:
        legacy_inventory[name] = get_or_create(
            db,
            models.Inventory,
            name=name,
            defaults={
                "unit": unit,
                "total": total,
                "used": used,
                "code": code,
                "section": section,
                "category": category,
            },
        )

    production_items = [
        ("MRD-COL-001", "Built-up Column C1", "ISMB 200", 6000, 12, "nos", 142.4, "painting"),
        ("MRD-BM-014", "Platform Beam B14", "ISMB 200", 7200, 8, "nos", 168.2, "fabrication"),
        ("MRD-PLT-022", "Base Plate BP22", "Plate 10mm", 450, 48, "nos", 8.1, "dispatch"),
    ]
    first_item = None
    for item_code, item_name, section, length_mm, quantity, unit, weight_per_unit, current_stage in production_items:
        item = get_or_create(
            db,
            models.ProductionItem,
            item_code=item_code,
            customer_id=customer.id,
            defaults={
                "item_name": item_name,
                "section": section,
                "length_mm": length_mm,
                "quantity": quantity,
                "unit": unit,
                "weight_per_unit": weight_per_unit,
                "current_stage": current_stage,
                "stage_updated_by": users["store"].id,
                "fabrication_deducted": current_stage != "fabrication",
                "material_deducted": current_stage != "fabrication",
                "is_completed": current_stage == "dispatch",
            },
        )
        first_item = first_item or item
        for stage in ["fabrication", "painting", "dispatch"]:
            status = "completed" if stage == current_stage or current_stage == "dispatch" else "pending"
            get_or_create(
                db,
                models.StageTracking,
                production_item_id=item.id,
                stage=stage,
                defaults={
                    "status": status,
                    "updated_by": users["store"].id,
                    "is_checked": status == "completed",
                    "completed_at": datetime.utcnow() if status == "completed" else None,
                },
            )

    get_or_create(
        db,
        models.MaterialMapping,
        excel_name="ISMB200",
        defaults={"material_id": legacy_inventory["ISMB 200 Beam"].id},
    )
    get_or_create(
        db,
        models.Instruction,
        message="Prioritize MRD-COL-001 painting before Friday dispatch planning.",
        created_by=users["boss"].id,
    )
    get_or_create(
        db,
        models.Query,
        title="Clarify primer coat thickness",
        defaults={
            "message": "Painting team needs confirmation on primer DFT for platform beams.",
            "customer_id": customer.id,
            "production_item_id": first_item.id,
            "stage": "painting",
            "created_by": users["qa"].id,
            "status": "IN_PROGRESS",
            "admin_reply": "Use the approved 70 micron DFT spec for this package.",
        },
    )
    get_or_create(
        db,
        models.Notification,
        message="Low stock alert: Paint Primer Red Oxide is below reorder threshold.",
        defaults={
            "role": "Store Keeper",
            "level": "warning",
            "category": "low_inventory",
            "read": False,
        },
    )
    get_or_create(
        db,
        models.ScrapRecord,
        material_name="MS Plate 10mm",
        defaults={
            "weight_kg": 112.5,
            "length_mm": 900,
            "width_mm": 160,
            "quantity": 11,
            "reason_code": "cutting_waste",
            "source_item_id": first_item.id,
            "source_customer_id": customer.id,
            "dimensions": "900mm x 160mm x 10mm",
            "notes": "Reusable after edge dressing",
            "status": "pending",
            "scrap_value": 4200.0,
            "created_by": users["store"].id,
        },
    )
    get_or_create(
        db,
        models.ReusableStock,
        material_name="ISMB 200 Beam Offcut",
        defaults={
            "length_mm": 1850,
            "width_mm": 100,
            "weight_kg": 78.4,
            "quantity": 3,
            "dimensions": "1850mm ISMB 200 offcut",
            "source_item_id": first_item.id,
            "source_customer_id": customer.id,
            "quality_grade": "A",
            "notes": "Good for stiffeners and small brackets",
            "is_available": True,
            "created_by": users["store"].id,
        },
    )
    return customer, legacy_inventory


def seed_inventory_v2(db, users, customer):
    vendor = get_or_create(
        db,
        models_v2.Vendor,
        code="VND-TATA",
        defaults={
            "name": "Tata Steel Distribution",
            "gstin": "20TATA1234F1Z8",
            "city": "Jamshedpur",
            "state": "Jharkhand",
            "contact_person": "Amit Sinha",
            "phone": "+91-98765-33003",
            "email": "amit.sinha@vendor.example",
            "is_active": True,
        },
    )
    location = get_or_create(
        db,
        models_v2.StorageLocation,
        code="YARD-A-01",
        defaults={
            "name": "Main Steel Yard A-01",
            "location_type": "yard",
            "capacity_tons": Decimal("250.000"),
            "current_occupancy_tons": Decimal("86.500"),
            "is_covered": False,
            "is_active": True,
        },
    )
    material = get_or_create(
        db,
        models_v2.MaterialMaster,
        code="STL-ISMB-200-E250",
        defaults={
            "name": "ISMB 200 Beam E250",
            "material_type": models_v2.MaterialType.BEAM,
            "grade": "IS 2062 E250",
            "specification": "Hot rolled structural beam, mill test certificate required.",
            "length_mm": Decimal("12000.00"),
            "default_unit": models_v2.WeightUnit.KG,
            "reorder_level": Decimal("3000.000"),
            "min_order_qty": Decimal("12000.000"),
            "category": "Structural",
            "sub_category": "Beam",
            "hsn_code": "7216",
            "is_active": True,
        },
    )
    plate = get_or_create(
        db,
        models_v2.MaterialMaster,
        code="STL-PLT-010-E250",
        defaults={
            "name": "MS Plate 10mm E250",
            "material_type": models_v2.MaterialType.PLATE,
            "grade": "IS 2062 E250",
            "thickness_mm": Decimal("10.000"),
            "width_mm": Decimal("1500.00"),
            "length_mm": Decimal("6000.00"),
            "default_unit": models_v2.WeightUnit.KG,
            "reorder_level": Decimal("2000.000"),
            "category": "Plate",
            "sub_category": "MS Plate",
            "hsn_code": "7208",
            "is_active": True,
        },
    )

    grn = get_or_create(
        db,
        models_v2.GoodsReceiptNote,
        grn_number="GRN/FY26/00017",
        defaults={
            "vendor_id": vendor.id,
            "vendor_invoice_number": "TS-INV-4581",
            "vendor_invoice_date": datetime(2026, 6, 1, 10, 30),
            "vehicle_number": "JH09BK4581",
            "driver_name": "Ramesh Kumar",
            "driver_contact": "+91-90000-11122",
            "gross_weight_kg": Decimal("20420.000"),
            "tare_weight_kg": Decimal("7420.000"),
            "net_weight_kg": Decimal("13000.000"),
            "weighbridge_slip_number": "WB-6129",
            "status": models_v2.DocumentStatus.APPROVED,
            "gate_entry_time": datetime(2026, 6, 1, 8, 20),
            "weighment_time": datetime(2026, 6, 1, 8, 52),
            "received_time": datetime(2026, 6, 1, 11, 15),
            "created_by": users["store"].id,
            "received_by": users["store"].id,
            "approved_by": users["boss"].id,
            "remarks": "Demo approved GRN with heat-traceable beam stock.",
        },
    )
    get_or_create(
        db,
        models_v2.GRNLineItem,
        grn_id=grn.id,
        material_id=material.id,
        defaults={
            "heat_number": "HT-26-ISM-4481",
            "batch_number": "BATCH-4481",
            "ordered_qty": Decimal("13000.000"),
            "received_qty": Decimal("13000.000"),
            "accepted_qty": Decimal("13000.000"),
            "rejected_qty": Decimal("0.000"),
            "unit": models_v2.WeightUnit.KG,
            "weight_kg": Decimal("13000.000"),
            "rate": Decimal("63.50"),
            "amount": Decimal("825500.00"),
            "qa_status": models_v2.QAStatus.APPROVED,
            "qa_remarks": "MTC verified.",
        },
    )
    lot = get_or_create(
        db,
        models_v2.StockLot,
        lot_number="LOT-FY26-00044",
        defaults={
            "material_id": material.id,
            "heat_number": "HT-26-ISM-4481",
            "batch_number": "BATCH-4481",
            "gross_weight_kg": Decimal("13000.000"),
            "tare_weight_kg": Decimal("0.000"),
            "net_weight_kg": Decimal("13000.000"),
            "current_weight_kg": Decimal("9175.000"),
            "initial_quantity": Decimal("108.000"),
            "current_quantity": Decimal("76.000"),
            "unit": models_v2.WeightUnit.KG,
            "vendor_id": vendor.id,
            "grn_id": grn.id,
            "purchase_rate": Decimal("63.50"),
            "qa_status": models_v2.QAStatus.APPROVED,
            "qa_remarks": "Released for fabrication.",
            "test_certificate_ref": "MTC-HT-4481",
            "location_id": location.id,
            "received_date": datetime(2026, 6, 1, 11, 15),
            "is_active": True,
            "is_blocked": False,
        },
    )
    get_or_create(
        db,
        models_v2.StockMovement,
        movement_number="MOV-FY26-00088",
        defaults={
            "stock_lot_id": lot.id,
            "movement_type": models_v2.MovementType.INWARD_PURCHASE,
            "weight_change_kg": Decimal("13000.000"),
            "weight_before_kg": Decimal("0.000"),
            "weight_after_kg": Decimal("13000.000"),
            "quantity_change": Decimal("108.000"),
            "reference_type": "grn",
            "reference_id": grn.id,
            "reference_number": grn.grn_number,
            "to_location_id": location.id,
            "reason": "Approved GRN receipt",
            "remarks": "Initial demo stock receipt",
            "created_by": users["store"].id,
            "approved_by": users["boss"].id,
            "approved_at": datetime(2026, 6, 1, 11, 20),
            "movement_date": datetime(2026, 6, 1, 11, 20),
            "valuation_rate": Decimal("63.5000"),
            "stock_value_change": Decimal("825500.00"),
            "balance_stock_value": Decimal("825500.00"),
            "balance_qty_kg": Decimal("13000.000"),
            "posting_date": date(2026, 6, 1),
            "fiscal_year": "FY2526",
        },
    )

    dispatch = get_or_create(
        db,
        models_v2.DispatchNote,
        dispatch_number="DSP/FY26/00009",
        defaults={
            "customer_id": customer.id,
            "sales_order_ref": "SO-MRD-2026-014",
            "vehicle_number": "JH09AF2201",
            "transporter": "Eastern Steel Logistics",
            "driver_name": "Manoj Prasad",
            "driver_contact": "+91-90000-22233",
            "gross_weight_kg": Decimal("12480.000"),
            "tare_weight_kg": Decimal("8420.000"),
            "net_weight_kg": Decimal("4060.000"),
            "status": models_v2.DocumentStatus.SUBMITTED,
            "created_by": users["dispatch"].id,
            "remarks": "Demo dispatch note awaiting boss approval.",
        },
    )
    get_or_create(
        db,
        models_v2.DispatchLineItem,
        dispatch_id=dispatch.id,
        stock_lot_id=lot.id,
        defaults={
            "dispatched_weight_kg": Decimal("3825.000"),
            "dispatched_qty": Decimal("32.000"),
            "rate": Decimal("82.00"),
            "amount": Decimal("313650.00"),
        },
    )
    return material, plate, lot


def seed_drawings_v3(db, users, customer, material, legacy_inventory):
    for idx, stage in enumerate(models_v3.DEFAULT_STAGES, start=1):
        get_or_create(
            db,
            models_v3.StageConfig,
            customer_id=customer.id,
            stage_name=stage["stage_name"],
            defaults={
                "sequence": idx,
                "is_mandatory": stage.get("is_mandatory", True),
                "requires_qa_hold": stage.get("requires_qa_hold", False),
                "auto_deduct_material": stage.get("auto_deduct_material", False),
            },
        )

    drawing = get_or_create(
        db,
        models_v3.Drawing,
        drawing_number="MRD-SHOP-001",
        revision="B",
        customer_id=customer.id,
        defaults={
            "title": "Metro Rail Depot Platform Truss",
            "project_ref": "MRD-PKG-06",
            "status": models_v3.DrawingStatus.IN_PROGRESS,
            "total_weight_kg": Decimal("8120.000"),
            "completed_weight_kg": Decimal("3480.000"),
            "released_date": datetime(2026, 6, 2, 9, 30),
            "released_by": users["boss"].id,
            "created_by": users["boss"].id,
            "notes": "Demo drawing with assembly/component level tracking.",
        },
    )
    assembly = get_or_create(
        db,
        models_v3.Assembly,
        drawing_id=drawing.id,
        mark_number="TRUSS-A",
        defaults={
            "description": "Main platform truss assembly",
            "quantity_required": 4,
            "quantity_complete": 1,
            "total_weight_kg": Decimal("8120.000"),
            "notes": "Each truss has chord beams and gusset plates.",
        },
    )
    component = get_or_create(
        db,
        models_v3.Component,
        assembly_id=assembly.id,
        piece_mark="TC-200-01",
        defaults={
            "profile_section": "ISMB 200",
            "grade": "IS 2062 E250",
            "length_mm": Decimal("7200.0"),
            "quantity_per_assembly": 2,
            "weight_each_kg": Decimal("168.200"),
            "material_id": material.id,
            "inventory_id": legacy_inventory["ISMB 200 Beam"].id,
            "notes": "Top chord member",
        },
    )
    for number, stage, status, completed in [
        (1, "painting", models_v3.ComponentStageStatus.IN_PROGRESS, False),
        (2, "qc", models_v3.ComponentStageStatus.PENDING, False),
        (3, "dispatch", models_v3.ComponentStageStatus.COMPLETED, True),
    ]:
        instance = get_or_create(
            db,
            models_v3.ComponentInstance,
            component_id=component.id,
            instance_number=number,
            defaults={
                "serial_tag": f"MRD-SHOP-001-TC-200-01-{number:02d}",
                "current_stage": stage,
                "stage_status": status,
                "stage_updated_at": datetime.utcnow(),
                "stage_updated_by": users["store"].id,
                "heat_number": "HT-26-ISM-4481",
                "is_completed": completed,
                "material_reserved": True,
                "material_issued": completed,
                "material_consumed": completed,
                "completed_at": datetime.utcnow() if completed else None,
            },
        )
        get_or_create(
            db,
            models_v3.MaterialReservation,
            component_instance_id=instance.id,
            defaults={
                "inventory_id": legacy_inventory["ISMB 200 Beam"].id,
                "reserved_weight_kg": Decimal("168.200"),
                "issued_weight_kg": Decimal("168.200") if completed else Decimal("0.000"),
                "consumed_weight_kg": Decimal("168.200") if completed else Decimal("0.000"),
                "status": models_v3.ReservationStatus.CONSUMED if completed else models_v3.ReservationStatus.RESERVED,
                "reserved_by": users["store"].id,
                "remarks": "Demo reservation for component tracking.",
            },
        )
        get_or_create(
            db,
            models_v3.StageTransition,
            component_instance_id=instance.id,
            to_stage=stage,
            defaults={
                "from_stage": "cutting",
                "from_status": "completed",
                "to_status": status.value if hasattr(status, "value") else str(status),
                "performed_by": users["store"].id,
                "station": "Shop Floor Bay 2",
                "remarks": "Seeded transition for demo board.",
            },
        )

    get_or_create(
        db,
        models_v3.DrawingRevision,
        drawing_id=drawing.id,
        from_revision="A",
        to_revision="B",
        defaults={
            "reason": "Added gusset plate stiffeners after design review.",
            "received_from": "Client design consultant",
            "bom_diff": {"added": 4, "modified": 2, "removed": 0},
            "approved_by": users["boss"].id,
            "approved_at": datetime(2026, 6, 3, 15, 15),
        },
    )


def seed_accounting(db):
    for code, name, account_type, is_group in [
        ("1000", "Assets", "asset", True),
        ("1100", "Stock In Hand", "asset", False),
        ("4000", "Sales", "income", False),
        ("5000", "Material Consumption", "expense", False),
    ]:
        get_or_create(
            db,
            models_accounting.Account,
            code=code,
            defaults={"name": name, "account_type": account_type, "is_group": is_group, "is_active": True},
        )
    get_or_create(
        db,
        models_accounting.FiscalYear,
        name="FY2526",
        defaults={
            "start_date": date(2025, 4, 1),
            "end_date": date(2026, 3, 31),
            "is_active": True,
        },
    )
    get_or_create(
        db,
        models_accounting.CostCenter,
        code="FAB",
        defaults={"name": "Fabrication Shop", "is_active": True},
    )


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        users = seed_users(db)
        seed_company_settings(db, users["admin"].id)
        customer, legacy_inventory = seed_legacy_operations(db, users)
        material, _plate, _lot = seed_inventory_v2(db, users, customer)
        seed_drawings_v3(db, users, customer, material, legacy_inventory)
        seed_accounting(db)
        db.commit()
        print("Demo data ready.")
        print("Login: admin / " + DEMO_PASSWORD)
        print("Database: " + str(engine.url))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
