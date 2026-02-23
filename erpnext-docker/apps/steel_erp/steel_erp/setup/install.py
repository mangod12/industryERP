"""
Steel ERP Installation and Setup Script
Creates initial data for Kumar Brothers Steel operations
"""

import frappe
from frappe import _


def after_install():
    """Run after app installation"""
    try:
        create_steel_item_groups()
        create_steel_uoms()
        create_steel_warehouses()
        create_steel_custom_fields()
        setup_company_defaults()
        frappe.db.commit()
        print("Steel ERP setup completed successfully!")
    except Exception as e:
        print(f"Steel ERP setup error: {e}")
        frappe.log_error(f"Steel ERP Installation Error: {e}")


def after_migrate():
    """Run after bench migrate"""
    try:
        create_steel_custom_fields()
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Steel ERP Migration Error: {e}")


def create_steel_item_groups():
    """Create steel industry specific item groups"""
    
    item_groups = [
        # Main parent group
        {
            "item_group_name": "Steel Products",
            "parent_item_group": "All Item Groups",
            "is_group": 1
        },
        # Sub-categories
        {
            "item_group_name": "MS Pipes",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Plates",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Beams",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Angles",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Channels",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Rounds",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Squares",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "MS Flats",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "GI Products",
            "parent_item_group": "Steel Products",
            "is_group": 1
        },
        {
            "item_group_name": "GI Pipes",
            "parent_item_group": "GI Products",
            "is_group": 0
        },
        {
            "item_group_name": "GI Sheets",
            "parent_item_group": "GI Products",
            "is_group": 0
        },
        {
            "item_group_name": "HR Products",
            "parent_item_group": "Steel Products",
            "is_group": 1
        },
        {
            "item_group_name": "HR Coils",
            "parent_item_group": "HR Products",
            "is_group": 0
        },
        {
            "item_group_name": "HR Sheets",
            "parent_item_group": "HR Products",
            "is_group": 0
        },
        {
            "item_group_name": "CR Products",
            "parent_item_group": "Steel Products",
            "is_group": 1
        },
        {
            "item_group_name": "CR Coils",
            "parent_item_group": "CR Products",
            "is_group": 0
        },
        {
            "item_group_name": "CR Sheets",
            "parent_item_group": "CR Products",
            "is_group": 0
        },
        {
            "item_group_name": "Structural Steel",
            "parent_item_group": "Steel Products",
            "is_group": 0
        },
        {
            "item_group_name": "Fabricated Items",
            "parent_item_group": "Steel Products",
            "is_group": 0
        }
    ]
    
    for group in item_groups:
        if not frappe.db.exists("Item Group", group["item_group_name"]):
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": group["item_group_name"],
                "parent_item_group": group["parent_item_group"],
                "is_group": group.get("is_group", 0)
            })
            doc.insert(ignore_permissions=True)
            print(f"Created Item Group: {group['item_group_name']}")


def create_steel_uoms():
    """Create steel industry specific UOMs"""
    
    uoms = [
        {"uom_name": "MT", "must_be_whole_number": 0},  # Metric Ton
        {"uom_name": "KG", "must_be_whole_number": 0},  # Kilogram
        {"uom_name": "Nos", "must_be_whole_number": 1}, # Numbers/Pieces
        {"uom_name": "Mtr", "must_be_whole_number": 0}, # Meters
        {"uom_name": "Feet", "must_be_whole_number": 0}, # Feet
        {"uom_name": "Inch", "must_be_whole_number": 0}, # Inches
        {"uom_name": "MM", "must_be_whole_number": 0},  # Millimeters
        {"uom_name": "Running Mtr", "must_be_whole_number": 0}, # Running Meters
        {"uom_name": "Bundle", "must_be_whole_number": 1}, # Bundles
        {"uom_name": "Coil", "must_be_whole_number": 1}, # Coils
    ]
    
    for uom in uoms:
        if not frappe.db.exists("UOM", uom["uom_name"]):
            doc = frappe.get_doc({
                "doctype": "UOM",
                "uom_name": uom["uom_name"],
                "must_be_whole_number": uom.get("must_be_whole_number", 0)
            })
            doc.insert(ignore_permissions=True)
            print(f"Created UOM: {uom['uom_name']}")


def create_steel_warehouses():
    """Create warehouses for steel operations"""
    
    # First check if a company exists
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    
    if not company:
        print("No company found, skipping warehouse creation")
        return
    
    warehouses = [
        {
            "warehouse_name": "Main Store",
            "warehouse_type": "Stores",
            "is_group": 0
        },
        {
            "warehouse_name": "Cutting Section",
            "warehouse_type": "Manufacturing",
            "is_group": 0
        },
        {
            "warehouse_name": "Dispatch Bay",
            "warehouse_type": "Transit",
            "is_group": 0
        },
        {
            "warehouse_name": "Quality Hold",
            "warehouse_type": "Stores",
            "is_group": 0
        },
        {
            "warehouse_name": "Scrap Yard",
            "warehouse_type": "Stores",
            "is_group": 0
        },
        {
            "warehouse_name": "Customer Goods",
            "warehouse_type": "Stores",
            "is_group": 0
        }
    ]
    
    for wh in warehouses:
        wh_name = f"{wh['warehouse_name']} - {frappe.db.get_value('Company', company, 'abbr')}"
        if not frappe.db.exists("Warehouse", wh_name):
            try:
                doc = frappe.get_doc({
                    "doctype": "Warehouse",
                    "warehouse_name": wh["warehouse_name"],
                    "warehouse_type": wh.get("warehouse_type", "Stores"),
                    "company": company,
                    "is_group": wh.get("is_group", 0)
                })
                doc.insert(ignore_permissions=True)
                print(f"Created Warehouse: {wh['warehouse_name']}")
            except Exception as e:
                print(f"Error creating warehouse {wh['warehouse_name']}: {e}")


def create_steel_custom_fields():
    """Create custom fields for steel industry"""
    
    custom_fields = {
        "Item": [
            {
                "fieldname": "steel_section",
                "label": "Steel Properties",
                "fieldtype": "Section Break",
                "insert_after": "description",
                "collapsible": 0
            },
            {
                "fieldname": "steel_grade",
                "label": "Steel Grade",
                "fieldtype": "Select",
                "options": "\nIS2062 E250\nIS2062 E350\nIS2062 E410\nSAIL MA 250\nSAIL MA 350\nSAIL MA 410\nSS304\nSS316\nSS202",
                "insert_after": "steel_section"
            },
            {
                "fieldname": "steel_type",
                "label": "Steel Type",
                "fieldtype": "Select",
                "options": "\nMild Steel (MS)\nGalvanized Iron (GI)\nHot Rolled (HR)\nCold Rolled (CR)\nStainless Steel (SS)",
                "insert_after": "steel_grade"
            },
            {
                "fieldname": "column_break_steel",
                "fieldtype": "Column Break",
                "insert_after": "steel_type"
            },
            {
                "fieldname": "material_shape",
                "label": "Shape",
                "fieldtype": "Select",
                "options": "\nPipe\nPlate\nSheet\nBeam\nAngle\nChannel\nRound\nSquare\nFlat\nCoil\nTMT Bar",
                "insert_after": "column_break_steel"
            },
            {
                "fieldname": "surface_finish",
                "label": "Surface Finish",
                "fieldtype": "Select",
                "options": "\nMill Finish\nGalvanized\nPainted\nPowder Coated\nPolished",
                "insert_after": "material_shape"
            },
            {
                "fieldname": "dimensions_section",
                "label": "Dimensions",
                "fieldtype": "Section Break",
                "insert_after": "surface_finish",
                "collapsible": 1
            },
            {
                "fieldname": "steel_length",
                "label": "Length (mm)",
                "fieldtype": "Float",
                "insert_after": "dimensions_section"
            },
            {
                "fieldname": "steel_width",
                "label": "Width (mm)",
                "fieldtype": "Float",
                "insert_after": "steel_length"
            },
            {
                "fieldname": "column_break_dim",
                "fieldtype": "Column Break",
                "insert_after": "steel_width"
            },
            {
                "fieldname": "steel_thickness",
                "label": "Thickness (mm)",
                "fieldtype": "Float",
                "insert_after": "column_break_dim"
            },
            {
                "fieldname": "steel_diameter",
                "label": "Diameter (mm)",
                "fieldtype": "Float",
                "insert_after": "steel_thickness"
            },
            {
                "fieldname": "weight_per_unit",
                "label": "Weight per Unit (KG)",
                "fieldtype": "Float",
                "insert_after": "steel_diameter"
            }
        ],
        "Stock Entry Detail": [
            {
                "fieldname": "heat_number",
                "label": "Heat Number",
                "fieldtype": "Data",
                "insert_after": "item_code"
            },
            {
                "fieldname": "mill_tc_number",
                "label": "Mill TC Number",
                "fieldtype": "Data",
                "insert_after": "heat_number"
            }
        ],
        "Purchase Receipt Item": [
            {
                "fieldname": "heat_number",
                "label": "Heat Number",
                "fieldtype": "Data",
                "insert_after": "item_code"
            },
            {
                "fieldname": "mill_weight",
                "label": "Mill Weight (KG)",
                "fieldtype": "Float",
                "insert_after": "heat_number"
            },
            {
                "fieldname": "actual_weight",
                "label": "Actual Weight (KG)",
                "fieldtype": "Float",
                "insert_after": "mill_weight"
            },
            {
                "fieldname": "weight_difference",
                "label": "Weight Difference",
                "fieldtype": "Float",
                "read_only": 1,
                "insert_after": "actual_weight"
            }
        ],
        "Delivery Note Item": [
            {
                "fieldname": "tracking_code",
                "label": "Tracking Code",
                "fieldtype": "Data",
                "insert_after": "item_code",
                "read_only": 1
            },
            {
                "fieldname": "heat_number",
                "label": "Heat Number",
                "fieldtype": "Data",
                "insert_after": "tracking_code"
            },
            {
                "fieldname": "bundle_no",
                "label": "Bundle/Lot Number",
                "fieldtype": "Data",
                "insert_after": "heat_number"
            }
        ],
        "Delivery Note": [
            {
                "fieldname": "transport_section",
                "label": "Transport Details",
                "fieldtype": "Section Break",
                "insert_after": "taxes_and_charges"
            },
            {
                "fieldname": "vehicle_no",
                "label": "Vehicle Number",
                "fieldtype": "Data",
                "insert_after": "transport_section"
            },
            {
                "fieldname": "driver_name",
                "label": "Driver Name",
                "fieldtype": "Data",
                "insert_after": "vehicle_no"
            },
            {
                "fieldname": "driver_mobile",
                "label": "Driver Mobile",
                "fieldtype": "Data",
                "insert_after": "driver_name"
            },
            {
                "fieldname": "column_break_transport",
                "fieldtype": "Column Break",
                "insert_after": "driver_mobile"
            },
            {
                "fieldname": "transporter",
                "label": "Transporter",
                "fieldtype": "Data",
                "insert_after": "column_break_transport"
            },
            {
                "fieldname": "lr_number",
                "label": "LR Number",
                "fieldtype": "Data",
                "insert_after": "transporter"
            },
            {
                "fieldname": "lr_date",
                "label": "LR Date",
                "fieldtype": "Date",
                "insert_after": "lr_number"
            }
        ],
        "Customer": [
            {
                "fieldname": "steel_customer_section",
                "label": "Steel Customer Details",
                "fieldtype": "Section Break",
                "insert_after": "customer_primary_contact"
            },
            {
                "fieldname": "gst_number",
                "label": "GST Number",
                "fieldtype": "Data",
                "insert_after": "steel_customer_section"
            },
            {
                "fieldname": "pan_number",
                "label": "PAN Number",
                "fieldtype": "Data",
                "insert_after": "gst_number"
            },
            {
                "fieldname": "credit_limit",
                "label": "Credit Limit",
                "fieldtype": "Currency",
                "insert_after": "pan_number"
            },
            {
                "fieldname": "credit_days",
                "label": "Credit Days",
                "fieldtype": "Int",
                "insert_after": "credit_limit"
            }
        ]
    }
    
    for doctype, fields in custom_fields.items():
        for field in fields:
            field_name = f"{doctype}-{field['fieldname']}"
            if not frappe.db.exists("Custom Field", field_name):
                try:
                    cf = frappe.get_doc({
                        "doctype": "Custom Field",
                        "dt": doctype,
                        "module": "Steel ERP",
                        **field
                    })
                    cf.insert(ignore_permissions=True)
                    print(f"Created Custom Field: {field['fieldname']} for {doctype}")
                except Exception as e:
                    print(f"Error creating field {field['fieldname']}: {e}")


def setup_company_defaults():
    """Setup default company configuration"""
    
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    
    if company:
        # Set default stock settings
        stock_settings = frappe.get_single("Stock Settings")
        stock_settings.auto_indent = 1
        stock_settings.auto_insert_price_list_rate_if_missing = 1
        stock_settings.allow_negative_stock = 0
        stock_settings.show_barcode_field = 1
        stock_settings.save(ignore_permissions=True)
        print("Updated Stock Settings")
