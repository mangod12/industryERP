# Steel ERP - ERPNext Customization for Steel Fabrication Industry

## Overview

**Steel ERP** is a comprehensive Frappe/ERPNext application designed specifically for the steel fabrication industry. It provides specialized production tracking, batch traceability with heat numbers, weighbridge integration, and automated inventory management.

This customization extends ERPNext to meet the specific requirements of KumarBrothers Steel's workflow:
- Production stage tracking (Fabrication → Painting → Dispatch → Completed)
- Automatic material deduction when fabrication completes
- Heat number and batch traceability for quality control
- Weighbridge integration for GRN and dispatch
- Scrap management with recovery tracking
- Reusable stock management for offcuts
- Excel/CSV import for production tracking

---

## Features

### 1. Steel Production Order (Custom DocType)
- Complete production workflow with sequential stages
- Links to Customer and Items
- Drawing numbers, assembly marks, and profiles
- Material requirements with auto-deduction
- Stage-wise tracking (Fabrication, Painting, Dispatch, Completed)
- Priority management (Low, Medium, High, Urgent)
- Overall completion percentage calculation

### 2. Production Stage Tracking
- **Fabrication Stage**: Material auto-deduction on completion
- **Painting Stage**: Paint specification tracking
- **Dispatch Stage**: Ready for delivery
- **Completed**: Final stage
- Stage-wise timestamps and operator tracking
- Cannot skip stages (enforced workflow)

### 3. Steel-Specific Custom Fields

#### Item DocType Extensions:
- Steel Grade (e.g., IS2062 E250, ASTM A36)
- Material Type (COIL, BILLET, SLAB, SHEET, BAR, PLATE, PIPE, ANGLE, CHANNEL, BEAM)
- Profile/Section (e.g., UB203X133X25, ISMC250)
- Thickness and Width dimensions
- HSN Code for GST compliance

#### Batch DocType Extensions:
- Heat Number (for traceability)
- Coil Number
- QA Status (Pending, Approved, Rejected, On Hold)
- Mill Certificate Reference
- Block Reason (for rejected/held batches)

#### Purchase Receipt & Delivery Note Extensions:
- Vehicle Number
- Driver Name
- Gross Weight (kg)
- Tare Weight (kg)
- Net Weight (auto-calculated)
- Weighbridge Slip Number
- Weighment Timestamp

### 4. Scrap Management (Custom DocType)
- Scrap recording with reason codes:
  - Cutting Waste
  - Defect
  - Damage
  - Overrun
  - Leftover
  - Quality Rejection
  - Handling Damage
  - Machine Error
- Recoverable vs non-recoverable scrap
- Financial impact tracking (estimated loss, recovery value, net loss)
- Source production order linkage
- Automatic stock entry creation

### 5. Reusable Stock (Custom DocType)
- Manage offcuts and recoverable materials
- Dimensions and quality grading (Grade A, B, C)
- Storage location tracking
- Allocation to production orders
- Usage tracking
- Search functionality for matching reusable stock

### 6. Excel/CSV Import Utility
- Flexible column mapping (supports 40+ variations)
- Auto-match profiles to Item master
- Preview before import with stock availability
- Bulk creation of Steel Production Orders
- Material requirement auto-creation
- Lot number assignment

### 7. Production Dashboard (Custom Page)
- Real-time overview of production status
- KPI cards: Total Orders, In Progress, Completed, On Hold
- Stage summary with counts (Not Started, In Progress, Completed)
- Inventory summary with utilization percentages
- Low stock alerts (>85% utilization = Critical, >70% = Low Stock)
- Auto-refresh every 10 seconds

### 8. Custom Reports

#### Production Stage Summary
- Filter by customer, status, stage, date range
- Shows all production orders with stage-wise status
- Completion percentage tracking
- Exportable to Excel/PDF

#### Scrap Analysis
- Total scrap by reason code
- Pie chart visualization
- Recoverable vs non-recoverable breakdown
- Financial loss tracking
- Summary statistics

#### Material Traceability (Planned)
- Heat number → Batch → Production → Dispatch tracking
- Quality certificate linkage
- Full supply chain visibility

---

## Installation

### Prerequisites
- Frappe Framework (v14 or v15)
- ERPNext installed
- Python 3.10+
- MariaDB/PostgreSQL

### Step 1: Install the App

```bash
# Navigate to your Frappe bench
cd ~/frappe-bench

# Get the app
bench get-app https://github.com/your-repo/steel_erp

# Install to your site
bench --site your-site.local install-app steel_erp

# Migrate database
bench --site your-site.local migrate
```

### Step 2: Setup Custom Fields

The custom fields are automatically created on installation. If needed, manually import:

```bash
bench --site your-site.local import-fixtures steel_erp
```

### Step 3: Configure Permissions

Assign roles to users:
- **Manufacturing Manager**: Full access to all Steel Production modules
- **Manufacturing User**: Create and update production orders
- **Stock User**: View inventory and reports

### Step 4: Initial Data Setup

1. **Create Item Groups** for steel products:
   - Steel Raw Materials
   - Steel Sections (Beams, Channels, Angles)
   - Steel Plates & Sheets

2. **Add Items** with custom fields:
   - Set `custom_profile_section` (e.g., "UB203X133X25")
   - Set `custom_steel_grade` (e.g., "IS2062 E250")
   - Set `custom_material_type` (e.g., "BEAM")
   - Enable "Has Batch No" for batch tracking

3. **Configure Warehouses**:
   - Raw Material Warehouse
   - Work-in-Progress Warehouse
   - Finished Goods Warehouse

4. **Setup Customers and Suppliers**

---

## Usage Workflow

### Complete Production Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEEL ERP WORKFLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. SETUP MASTER DATA
   └─> Add Items with profile_section (e.g., UB203X133X25)
   └─> Add Customers

2. IMPORT TRACKING EXCEL
   └─> Upload CSV/Excel with columns: Drawing No, PROFILE, QTY, WT-(kg)
   └─> System auto-matches PROFILE to Items
   └─> Creates Steel Production Orders in Fabrication stage

3. TRACK PRODUCTION
   └─> Start Fabrication → In Progress
   └─> Complete Fabrication → Materials auto-deducted from inventory
   └─> Start Painting → In Progress
   └─> Complete Painting → Moves to Dispatch
   └─> Complete Dispatch → Moves to Completed

4. MONITOR DASHBOARD
   └─> Real-time stage counts
   └─> Inventory utilization
   └─> Low stock alerts
```

### Excel Import Example

**CSV File Format:**
```csv
Drawing no,ASSEMBLY,NAME,PROFILE,QTY.,WT-(kg),PAINT,LOT 1
DWG-001,B1,BEAM,UB203X133X25,1,45.6,,Lot-A
DWG-002,B2,COLUMN,ISMC250,2,38.5,Red Paint,Lot-A
```

**Import Steps:**
1. Navigate to Steel Production module
2. Click "Import from Excel"
3. Upload file
4. Review preview (shows matched vs unmatched profiles)
5. Confirm import
6. System creates Steel Production Orders with:
   - Customer linkage
   - Material requirements
   - Default stages (Fabrication, Painting, Dispatch, Completed)

---

## API Documentation

### Whitelisted Methods

#### Import Excel
```python
frappe.call({
    method: 'steel_erp.steel_production.utils.excel_import.import_tracking_excel',
    args: {
        file_path: '/path/to/file.xlsx',
        customer: 'Customer Name',
        lot_number: 'LOT-001'
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```

#### Start Production Stage
```python
doc = frappe.get_doc("Steel Production Order", "SPO-CUST-00001")
doc.start_stage("Fabrication")
```

#### Complete Production Stage
```python
doc = frappe.get_doc("Steel Production Order", "SPO-CUST-00001")
doc.complete_stage("Fabrication")  # Triggers material deduction
```

#### Search Reusable Stock
```python
frappe.call({
    method: 'steel_erp.steel_inventory.doctype.reusable_stock.reusable_stock.search_reusable_stock',
    args: {
        material_item: 'UB203X133X25',
        min_weight: 50,
        quality_grade: 'Grade A - Excellent'
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```

---

## Customization Guide

### Adding New Production Stages

Edit [steel_production_order.py](steel_erp/steel_production/doctype/steel_production_order/steel_production_order.py):

```python
def add_default_stages(self):
    default_stages = [
        "Fabrication", 
        "Painting", 
        "Quality Check",  # NEW STAGE
        "Dispatch", 
        "Completed"
    ]
    # ... rest of code
```

### Customizing Material Deduction Logic

Edit [steel_production/__init__.py](steel_erp/steel_production/__init__.py):

```python
def create_material_stock_entry(production_order):
    # Modify stock entry creation logic
    # Add custom valuation, FIFO logic, etc.
```

### Adding Custom Notifications

Edit [hooks.py](steel_erp/hooks.py):

```python
doc_events = {
    "Steel Production Order": {
        "on_update": "steel_erp.steel_production.on_stage_change",
        "on_submit": "steel_erp.steel_production.on_production_submit",
        "on_cancel": "your_custom_module.cancel_handler",  # NEW
    }
}
```

---

## Troubleshooting

### Issue: Custom fields not appearing
**Solution:**
```bash
bench --site your-site.local migrate
bench --site your-site.local clear-cache
```

### Issue: Material deduction not working
**Check:**
1. Material Requirements table is populated
2. Warehouse is set in material requirements
3. Item exists in inventory with sufficient stock
4. Check Error Log for exceptions

### Issue: Excel import fails
**Check:**
1. File format (CSV or XLSX)
2. Column names match expected variations
3. Items exist with matching `custom_profile_section`
4. Check browser console for detailed errors

---

## Module Structure

```
steel_erp/
├── hooks.py                          # Frappe app hooks
├── modules.txt                       # Module list
├── fixtures/                         # Custom field definitions
│   ├── custom_fields_item.json
│   ├── custom_fields_batch.json
│   ├── custom_fields_purchase_receipt.json
│   ├── custom_fields_delivery_note.json
│   └── custom_fields_stock_entry.json
├── steel_production/                 # Production module
│   ├── __init__.py                   # Hooks and utilities
│   ├── doctype/
│   │   ├── steel_production_order/   # Main DocType
│   │   ├── production_stage/         # Child table
│   │   └── production_material_requirement/
│   ├── page/
│   │   └── production_dashboard/     # Custom dashboard
│   ├── report/
│   │   └── production_stage_summary/ # Custom report
│   └── utils/
│       └── excel_import.py           # Import utility
├── steel_inventory/                  # Inventory module
│   ├── __init__.py                   # Inventory hooks
│   ├── doctype/
│   │   ├── scrap_record/
│   │   └── reusable_stock/
│   └── report/
│       └── scrap_analysis/           # Scrap report
└── steel_quality/                    # Quality module (future)
```

---

## Roadmap

### Phase 1: Core Features ✅ (Completed)
- [x] Steel Production Order DocType
- [x] Stage tracking with automation
- [x] Custom fields for Item, Batch, PR, DN
- [x] Scrap Record management
- [x] Reusable Stock management
- [x] Excel import utility
- [x] Production Dashboard
- [x] Basic reports

### Phase 2: Advanced Features (Planned)
- [ ] Material Traceability Report (Heat Number → Dispatch)
- [ ] FIFO/FEFO picking algorithm for batch selection
- [ ] QR code generation for batches and production orders
- [ ] Mobile app for shop floor updates
- [ ] Barcode scanning integration

### Phase 3: Integration (Planned)
- [ ] Weighbridge device API integration
- [ ] Email/SMS notifications
- [ ] WhatsApp integration for status updates
- [ ] Power BI/Analytics dashboard connector
- [ ] API for third-party ERP integration

---

## Support & Contributing

### Documentation
- [ERPNext Documentation](https://docs.erpnext.com/)
- [Frappe Framework](https://frappeframework.com/)

### Contact
- **Developer**: KumarBrothers Steel IT Team
- **Email**: info@kumarbrothers.com

### License
MIT License - See LICENSE file for details

---

## Credits

Built with:
- [Frappe Framework](https://frappeframework.com/)
- [ERPNext](https://erpnext.com/)
- Python, JavaScript, MariaDB

Developed for **KumarBrothers Steel** fabrication operations.
