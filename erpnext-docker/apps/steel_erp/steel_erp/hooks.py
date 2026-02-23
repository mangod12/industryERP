"""
Steel ERP Hooks - Frappe Application Configuration
"""

app_name = "steel_erp"
app_title = "Steel ERP"
app_publisher = "Kumar Brothers Steel"
app_description = "Steel Fabrication Industry Solution for ERPNext"
app_email = "admin@kumarbrothers.com"
app_license = "MIT"
app_version = "1.0.0"

# Required Apps
required_apps = ["frappe", "erpnext"]

# App Icon and Color
app_icon = "octicon octicon-package"
app_color = "#2E86AB"

# Includes in <head>
# ------------------
# app_include_css = "/assets/steel_erp/css/steel_erp.css"
# app_include_js = "/assets/steel_erp/js/steel_erp.js"

# Installation Hook
after_install = "steel_erp.setup.install.after_install"
after_migrate = "steel_erp.setup.install.after_migrate"

# Document Events
doc_events = {
    "Stock Entry": {
        "validate": "steel_erp.events.stock_entry.validate_stock_entry",
        "on_submit": "steel_erp.events.stock_entry.on_submit_stock_entry",
    },
    "Delivery Note": {
        "validate": "steel_erp.events.delivery_note.validate_delivery_note",
        "on_submit": "steel_erp.events.delivery_note.on_submit_delivery_note",
        "on_cancel": "steel_erp.events.delivery_note.on_cancel_delivery_note"
    },
    "Purchase Receipt": {
        "validate": "steel_erp.events.purchase_receipt.validate_purchase_receipt",
        "on_submit": "steel_erp.events.purchase_receipt.on_submit_purchase_receipt",
        "on_cancel": "steel_erp.events.purchase_receipt.on_cancel_purchase_receipt"
    },
    "Item": {
        "validate": "steel_erp.events.item.validate_item",
        "on_update": "steel_erp.events.item.on_update_item"
    }
}

# Fixtures - Export to JSON
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Steel ERP"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "=", "Steel ERP"]]
    }
]

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "steel_erp.tasks.scheduled.daily"
    ],
    "weekly": [
        "steel_erp.tasks.scheduled.weekly"
    ]
}

# Jinja Template Extensions
jinja = {
    "methods": [
        "steel_erp.utils.jinja_methods.format_steel_dimensions",
        "steel_erp.utils.jinja_methods.format_weight",
        "steel_erp.utils.jinja_methods.get_steel_grade_display"
    ]
}

# Override Standard Doctype Classes
override_doctype_class = {
    "Item": "steel_erp.overrides.item.SteelItem",
    "Stock Entry": "steel_erp.overrides.stock_entry.SteelStockEntry"
}

# Default Settings
default_mail_footer = """
<div style="text-align: center; color: #888; padding: 10px;">
    <p>Kumar Brothers Steel - Quality Steel Solutions</p>
    <p>Powered by ERPNext + Steel ERP</p>
</div>
"""
