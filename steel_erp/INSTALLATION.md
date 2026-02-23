# Steel ERP Installation & Setup Guide

## Quick Start

Follow these steps to install and configure Steel ERP in your ERPNext instance.

---

## Prerequisites

- **Frappe Framework**: v14 or v15
- **ERPNext**: v14 or v15 installed
- **Python**: 3.10 or higher
- **Database**: MariaDB 10.6+ or PostgreSQL 13+
- **Node.js**: v16 or higher
- **Operating System**: Ubuntu 20.04+, macOS, or Windows (WSL)

---

## Installation Steps

### Step 1: Navigate to Bench Directory

```bash
cd ~/frappe-bench
```

### Step 2: Add Steel ERP App to Bench

Since this is a local development app, copy the steel_erp folder to the apps directory:

```bash
# Copy steel_erp to bench apps directory
cp -r /path/to/next_project/steel_erp ~/frappe-bench/apps/

# OR create symlink for development
ln -s /path/to/next_project/steel_erp ~/frappe-bench/apps/steel_erp
```

### Step 3: Install App on Site

```bash
# Install the app
bench --site your-site.local install-app steel_erp

# Migrate database to create custom DocTypes
bench --site your-site.local migrate

# Clear cache
bench --site your-site.local clear-cache
```

### Step 4: Build Assets

```bash
# Build JavaScript and CSS files
bench build --app steel_erp

# Restart bench
bench restart
```

---

## Post-Installation Setup

### 1. Import Custom Fields

Custom fields are automatically created during migration. Verify they exist:

```bash
# Check custom fields
bench --site your-site.local console

# In Python console:
>>> import frappe
>>> frappe.get_all("Custom Field", filters={"dt": "Item", "fieldname": ["like", "custom_steel_%"]})
```

If custom fields are missing:

```bash
bench --site your-site.local import-fixtures steel_erp
```

### 2. Configure Permissions

Navigate to: **Setup → Permissions → Role Permissions Manager**

Recommended role setup:

| Role | Permissions |
|------|------------|
| **Manufacturing Manager** | All: Steel Production Order, Scrap Record, Reusable Stock |
| **Manufacturing User** | Create, Read, Write: Steel Production Order |
| **Stock User** | Read: All steel modules, Reports |

### 3. Setup Master Data

#### A. Create Item Groups

Navigate to: **Stock → Item Group**

Create hierarchy:
```
All Item Groups
└── Steel Materials
    ├── Steel Raw Materials
    ├── Steel Sections
    │   ├── Beams
    │   ├── Channels
    │   └── Angles
    └── Steel Plates & Sheets
```

#### B. Add Items with Steel Specifications

Navigate to: **Stock → Item**

Create items for each profile/section:

**Example: UB203X133X25**
- Item Code: `UB203X133X25`
- Item Name: `Universal Beam 203x133x25`
- Item Group: `Steel Sections → Beams`
- Stock UOM: `Kg`
- **Custom Fields:**
  - Steel Grade: `IS2062 E250`
  - Material Type: `BEAM`
  - Profile/Section: `UB203X133X25`
  - Thickness (mm): `25`
  - HSN Code: `7216`
- Enable "Maintain Stock": ✅
- Enable "Has Batch No": ✅ (for heat number tracking)

**Repeat for all profiles** (ISMC250, ISA75X75X6, etc.)

#### C. Setup Warehouses

Navigate to: **Stock → Warehouse**

Create warehouses:
- **Raw Material Warehouse** - For incoming steel
- **WIP Warehouse** - Work in Progress
- **Finished Goods Warehouse** - Completed items
- **Scrap Yard** - Scrap storage
- **Reusable Stock Warehouse** - Offcuts

#### D. Add Customers

Navigate to: **Selling → Customer**

Create customers with project details.

---

## Configuration

### 1. Company Settings

Navigate to: **Setup → Company**

Set default accounts:
- Default Expense Account
- Default Cost Center
- Default Warehouse

### 2. Stock Settings

Navigate to: **Stock → Stock Settings**

Configure:
- Default Warehouse
- Default Valuation Method: **FIFO** (recommended for steel traceability)
- Enable "Allow Negative Stock": No (enforce stock availability)

### 3. Manufacturing Settings

Navigate to: **Manufacturing → Manufacturing Settings**

Configure:
- Default Work In Progress Warehouse
- Backflush Raw Materials Based On: **Material Transferred for Manufacture**

---

## Verification

### Test 1: Create Steel Production Order

```bash
# Via UI:
1. Go to Steel Production → Steel Production Order → New
2. Fill in:
   - Customer: Select customer
   - Item Code: UB203X133X25
   - Drawing Number: TEST-001
   - Quantity: 1
   - Weight Per Unit: 45.6
3. Save
4. Submit
5. Verify production stages are created
```

### Test 2: Import Excel File

```bash
# Prepare test CSV:
Drawing no,ASSEMBLY,PROFILE,QTY.,WT-(kg)
TEST-001,B1,UB203X133X25,1,45.6
TEST-002,B2,ISMC250,2,38.5

# Import via Python console:
>>> from steel_erp.steel_production.utils.excel_import import import_tracking_excel
>>> result = import_tracking_excel("/path/to/test.csv", "Test Customer")
>>> print(result)
```

### Test 3: View Production Dashboard

Navigate to: **Steel Production → Production Dashboard**

Verify:
- KPI cards show correct counts
- Stage summary displays data
- Inventory summary shows items

---

## Integration with Existing Data

### Migrate from Custom System

If migrating from the existing backend_core system:

#### 1. Export Existing Data

```bash
cd /path/to/next_project

# Export customers
python backend_core/app/customers.py export_customers > customers.json

# Export inventory
python backend_core/app/inventory.py export_inventory > inventory.json

# Export production items
python backend_core/app/tracking.py export_production > production.json
```

#### 2. Import to ERPNext

```bash
# Create migration script
bench --site your-site.local console

# In Python console:
>>> from steel_erp.migration import import_customers, import_inventory, import_production
>>> import_customers("customers.json")
>>> import_inventory("inventory.json")
>>> import_production("production.json")
```

---

## Troubleshooting

### Issue: App not listed in installed apps

**Solution:**
```bash
# Reinstall
bench --site your-site.local uninstall-app steel_erp
bench --site your-site.local install-app steel_erp
```

### Issue: Custom DocTypes not visible

**Check:**
1. DocType JSON files are in correct folders
2. Module is listed in modules.txt
3. Run migrate again:
   ```bash
   bench --site your-site.local migrate
   ```

### Issue: Permission errors

**Solution:**
```bash
# Reset permissions
bench --site your-site.local set-admin-password admin
bench --site your-site.local add-system-manager [user@example.com]
```

### Issue: Frontend assets not loading

**Solution:**
```bash
bench build --app steel_erp --force
bench restart
```

---

## Development Mode

For development and testing:

```bash
# Enable developer mode
bench --site your-site.local set-config developer_mode 1

# Watch for changes
bench watch

# In separate terminal
bench start
```

---

## Production Deployment

### 1. Setup Production Config

```bash
# Disable developer mode
bench --site your-site.local set-config developer_mode 0

# Setup production
sudo bench setup production [frappe-user]

# Enable supervisor
sudo bench setup supervisor
sudo supervisorctl restart all

# Enable nginx
sudo bench setup nginx
sudo service nginx reload
```

### 2. Setup SSL (Optional)

```bash
sudo bench setup lets-encrypt [site-name]
```

### 3. Backup Strategy

```bash
# Setup automatic backups
bench --site your-site.local backup --with-files

# Add to crontab (daily at 2 AM)
0 2 * * * cd ~/frappe-bench && bench --site your-site.local backup --with-files
```

---

## Next Steps

1. ✅ Complete master data setup (Items, Customers, Warehouses)
2. ✅ Test Excel import with sample tracking file
3. ✅ Create first Steel Production Order
4. ✅ Complete production workflow (Fabrication → Painting → Dispatch)
5. ✅ Verify material deduction
6. ✅ Train users on dashboard and reports

---

## Support

For installation issues:
- Check ERPNext Forum: https://discuss.erpnext.com/
- Frappe Framework Docs: https://frappeframework.com/docs
- ERPNext Documentation: https://docs.erpnext.com/

For Steel ERP specific issues:
- Contact: info@kumarbrothers.com
