# Steel ERP - Quick Reference Guide

## 🚀 Quick Commands

### Installation
```bash
cd ~/frappe-bench
cp -r /path/to/steel_erp apps/
bench --site yoursite.local install-app steel_erp
bench --site yoursite.local migrate
bench build --app steel_erp
bench restart
```

### Development
```bash
bench --site yoursite.local set-config developer_mode 1
bench watch
bench start
```

### Production
```bash
sudo bench setup production [user]
sudo bench setup supervisor
sudo bench setup nginx
sudo service nginx reload
```

---

## 📋 Key DocTypes

| DocType | Purpose | Naming |
|---------|---------|--------|
| Steel Production Order | Production tracking | SPO-{customer}-##### |
| Scrap Record | Waste management | SCR-{YYYY}-##### |
| Reusable Stock | Offcut management | RUS-{YYYY}-##### |

---

## 🔄 Production Workflow

```
Steel Production Order
    ↓ Submit
Fabrication (Not Started)
    ↓ start_stage("Fabrication")
Fabrication (In Progress)
    ↓ complete_stage("Fabrication") → Auto-deduct materials
Painting (In Progress)
    ↓ complete_stage("Painting")
Dispatch (In Progress)
    ↓ complete_stage("Dispatch")
Completed ✅
```

---

## 💡 Common Tasks

### Create Production Order
```python
doc = frappe.new_doc("Steel Production Order")
doc.customer = "Customer Name"
doc.item_code = "UB203X133X25"
doc.drawing_number = "DWG-001"
doc.quantity = 1
doc.weight_per_unit = 45.6
doc.insert()
doc.submit()
```

### Import Excel
```python
from steel_erp.steel_production.utils.excel_import import import_tracking_excel

result = import_tracking_excel(
    file_path="/path/to/tracking.xlsx",
    customer="Customer Name",
    lot_number="LOT-001"
)
```

### Start/Complete Stage
```python
doc = frappe.get_doc("Steel Production Order", "SPO-CUST-00001")
doc.start_stage("Fabrication")
doc.complete_stage("Fabrication")  # Triggers material deduction
```

### Create Scrap Record
```python
scrap = frappe.new_doc("Scrap Record")
scrap.material_item = "UB203X133X25"
scrap.weight_kg = 12.5
scrap.reason_code = "Cutting Waste"
scrap.recoverable = 1  # Can be reused
scrap.insert()
scrap.submit()
```

### Search Reusable Stock
```python
from steel_erp.steel_inventory.doctype.reusable_stock.reusable_stock import search_reusable_stock

stocks = search_reusable_stock(
    material_item="UB203X133X25",
    min_weight=50,
    quality_grade="Grade A - Excellent"
)
```

---

## 🎯 Custom Fields Quick Reference

### Item
- `custom_steel_grade` - IS2062 E250, ASTM A36
- `custom_material_type` - COIL, BEAM, SHEET, BAR, PLATE, PIPE, ANGLE, CHANNEL
- `custom_profile_section` - UB203X133X25, ISMC250
- `custom_thickness_mm` - Thickness in mm
- `custom_width_mm` - Width in mm
- `custom_hsn_code` - HSN code

### Batch
- `custom_heat_number` - Heat/melt number
- `custom_coil_number` - Coil ID
- `custom_qa_status` - Pending, Approved, Rejected, On Hold
- `custom_mill_certificate_ref` - Certificate reference
- `custom_block_reason` - Reason for hold/rejection

### Purchase Receipt / Delivery Note
- `custom_vehicle_number` - Truck number
- `custom_driver_name` - Driver name
- `custom_gross_weight` - Weighbridge gross
- `custom_tare_weight` - Vehicle tare
- `custom_net_weight` - Calculated net
- `custom_weighbridge_slip_no` - Slip reference
- `custom_weighment_time` - Timestamp

---

## 📊 Dashboard & Reports

### Production Dashboard
**URL**: `/app/production-dashboard`

**Features**:
- KPI cards (Total, In Progress, Completed, On Hold)
- Stage summary by status
- Inventory utilization
- Auto-refresh every 10 seconds

### Production Stage Summary Report
**Path**: Steel Production → Reports → Production Stage Summary

**Filters**:
- Customer
- Status
- Current Stage
- Date Range

### Scrap Analysis Report
**Path**: Steel Inventory → Reports → Scrap Analysis

**Features**:
- Pie chart by reason code
- Recoverable vs non-recoverable
- Financial loss tracking
- Summary statistics

---

## 🔍 Troubleshooting

### Custom Fields Not Showing
```bash
bench --site yoursite.local migrate
bench --site yoursite.local clear-cache
bench restart
```

### Material Deduction Failed
**Check**:
1. Material Requirements populated?
2. Warehouse set?
3. Sufficient stock?
4. Error Log: `/app/error-log`

### Excel Import Issues
**Check**:
1. Column names match expected variations
2. Items exist with matching `custom_profile_section`
3. Browser console for errors
4. Python console:
```python
from steel_erp.steel_production.utils.excel_import import preview_excel_import
result = preview_excel_import("/path/to/file.xlsx")
print(result)
```

### Dashboard Not Loading
```bash
bench build --app steel_erp --force
bench restart
```

---

## 📖 Excel Import Column Mappings

Supported variations (case-insensitive):

| Field | Variations |
|-------|-----------|
| Drawing Number | drawing no, dwg no, drawing_no, dwg_no, drawing, item code, item_code |
| Assembly | assembly, assembly mark, asm, mark |
| Item Name | name, item name, item_name, description, desc |
| Profile | profile, section, profile/section, profile_section, material |
| Quantity | qty., qty, quantity, no., nos, no_of_items |
| Weight | wt-(kg), wt (kg), weight, wt, weight_kg, unit_weight |
| Area | ar(m²), ar (m²), area, ar, area_m2 |
| Paint | paint, paint_spec, painting |
| Lot | lot 1, lot_1, lot1, lot, batch, lot number |
| Priority | priority, area, location |

---

## 🔐 Permissions

### Manufacturing Manager
- Full access to all Steel modules
- Can create, edit, delete, submit
- Access to all reports

### Manufacturing User
- Create and update Steel Production Orders
- Can start/complete stages
- Read-only on reports

### Stock User
- Read-only on all Steel modules
- Full access to reports
- Can view inventory

---

## 📞 Support

**Documentation**:
- README.md - Feature overview
- INSTALLATION.md - Setup guide
- IMPLEMENTATION_SUMMARY.md - Complete details

**ERPNext Resources**:
- Forum: https://discuss.erpnext.com/
- Docs: https://docs.erpnext.com/
- Frappe: https://frappeframework.com/

**Contact**:
- Email: info@kumarbrothers.com

---

## ⚡ Performance Tips

1. **Enable Caching**:
```bash
bench --site yoursite.local set-config enable_redis_cache 1
```

2. **Optimize Queries**:
- Add indexes on frequently searched fields
- Use filters in reports

3. **Background Jobs**:
- Use RQ for heavy operations
- Schedule reports during off-peak hours

4. **Database Maintenance**:
```bash
# Backup
bench --site yoursite.local backup --with-files

# Optimize
bench --site yoursite.local mariadb
> OPTIMIZE TABLE `tabSteel Production Order`;
```

---

## 🎉 Quick Start Checklist

- [ ] Install Steel ERP app
- [ ] Migrate database
- [ ] Create Item Groups (Steel Materials, Sections, Plates)
- [ ] Add Items with profiles (UB203X133X25, ISMC250, etc.)
- [ ] Enable "Has Batch No" on Items
- [ ] Create Warehouses (Raw Material, WIP, Finished Goods)
- [ ] Add Customers
- [ ] Import tracking Excel
- [ ] Create first Steel Production Order
- [ ] Complete production workflow
- [ ] View Production Dashboard
- [ ] Generate reports

---

**Version**: 1.0.0  
**Last Updated**: February 2, 2026  
**Status**: Production Ready ✅
