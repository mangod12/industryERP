# Kumar Brothers Steel ERP

## Complete Steel Fabrication Solution powered by ERPNext

This is a customized ERPNext deployment specifically designed for steel fabrication industry operations, tailored for Kumar Brothers Steel.

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Windows 10/11 (or Linux/macOS)
- At least 4GB RAM available for Docker

### Deployment

1. **Open PowerShell/Terminal in the project folder:**
   ```powershell
   cd c:\Users\ansha\Downloads\next_project\erpnext-docker
   ```

2. **Start the deployment:**
   ```powershell
   docker-compose up -d
   ```

3. **Monitor the startup (first run takes 2-5 minutes):**
   ```powershell
   docker-compose logs -f erpnext
   ```

4. **Access ERPNext:**
   - URL: http://localhost:8080
   - Username: `Administrator`
   - Password: `KumarAdmin@2026`

---

## 📋 What's Included

### ERPNext v15 with Steel Industry Customizations:

#### Custom Fields for Items
| Field | Description |
|-------|-------------|
| Steel Grade | IS2062 E250, E350, E410, SAIL MA, SS304, SS316, etc. |
| Steel Type | MS, GI, HR, CR, Stainless Steel |
| Material Shape | Pipe, Plate, Sheet, Beam, Angle, Channel, Round, etc. |
| Surface Finish | Mill Finish, Galvanized, Painted, Powder Coated |
| Dimensions | Length, Width, Thickness, Diameter (in mm) |
| Weight per Unit | Auto-calculated based on dimensions |

#### Custom Fields for Transactions
- **Purchase Receipt**: Heat Number, Mill Weight, Actual Weight, Weight Difference
- **Delivery Note**: Tracking Code, Vehicle Number, Driver Details, LR Number
- **Stock Entry**: Heat Number, Mill TC Number
- **Customer**: GST Number, PAN Number, Credit Limit, Credit Days

#### Pre-configured Item Groups
- Steel Products (Parent)
  - MS Pipes, Plates, Beams, Angles, Channels, Rounds, Squares, Flats
  - GI Products (Pipes, Sheets)
  - HR Products (Coils, Sheets)
  - CR Products (Coils, Sheets)
  - Structural Steel
  - Fabricated Items

#### Steel-specific UOMs
- MT (Metric Ton)
- KG (Kilogram)
- Nos (Numbers)
- Mtr (Meters)
- Feet, Inch, MM
- Running Mtr
- Bundle, Coil

---

## 🔧 Management Commands

### Start Services
```powershell
docker-compose up -d
```

### Stop Services
```powershell
docker-compose down
```

### View Logs
```powershell
docker-compose logs -f erpnext
```

### Access ERPNext Console
```powershell
docker-compose exec erpnext bench --site kumar.local console
```

### Backup Site
```powershell
docker-compose exec erpnext bench --site kumar.local backup
```

### Run Migrations
```powershell
docker-compose exec erpnext bench --site kumar.local migrate
```

### Restart ERPNext
```powershell
docker-compose restart erpnext
```

### Complete Reset (CAUTION: Deletes all data)
```powershell
docker-compose down -v
docker-compose up -d
```

---

## 📁 File Structure

```
erpnext-docker/
├── docker-compose.yml      # Main Docker configuration
├── .env                    # Environment variables
├── deploy.bat              # Windows deployment script
├── stop.bat                # Windows stop script
├── scripts/
│   └── init-site.sh        # Site initialization script
└── apps/
    └── steel_erp/          # Custom Steel ERP App
        ├── package.json
        ├── pyproject.toml
        ├── README.md
        └── steel_erp/
            ├── __init__.py
            ├── hooks.py        # Frappe app configuration
            ├── modules.txt
            ├── setup/
            │   ├── __init__.py
            │   └── install.py  # Installation script
            ├── events/
            │   ├── __init__.py
            │   ├── item.py
            │   ├── stock_entry.py
            │   ├── delivery_note.py
            │   └── purchase_receipt.py
            ├── tasks/
            │   ├── __init__.py
            │   └── scheduled.py
            ├── overrides/
            │   ├── __init__.py
            │   ├── item.py
            │   └── stock_entry.py
            └── utils/
                ├── __init__.py
                ├── steel_calculations.py
                └── jinja_methods.py
```

---

## 🔐 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| ERPNext Admin | Administrator | KumarAdmin@2026 |
| MariaDB Root | root | kumar_root_2026 |

---

## 💡 Post-Setup Tasks

After first login, complete these setup steps:

1. **Setup Wizard**
   - Company Name: Kumar Brothers Steel
   - Country: India
   - Currency: INR
   - Fiscal Year: April - March

2. **Create Warehouses**
   - Main Store
   - Cutting Section
   - Dispatch Bay
   - Quality Hold
   - Scrap Yard

3. **Import Customers** (from existing system)
4. **Import Items** (steel inventory)
5. **Configure Print Formats**
6. **Setup Email** (for notifications)

---

## 🆘 Troubleshooting

### Site not loading / 404 Error
```powershell
# Check container status
docker-compose ps

# View erpnext logs
docker-compose logs erpnext

# Restart the service
docker-compose restart erpnext
```

### Database Connection Error
```powershell
# Check MariaDB is running
docker-compose logs mariadb

# Restart MariaDB
docker-compose restart mariadb

# Wait 30 seconds, then restart erpnext
docker-compose restart erpnext
```

### Reset Everything (Fresh Start)
```powershell
docker-compose down -v --remove-orphans
docker-compose up -d
```

---

## 📞 Support

For issues or customization requests:
- Check container logs first: `docker-compose logs -f`
- Review the ERPNext documentation: https://docs.erpnext.com/
- Frappe documentation: https://frappeframework.com/docs/

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   MariaDB   │  │ Redis Cache │  │  Redis Queue    │  │
│  │  (Database) │  │  (Caching)  │  │  (Background)   │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │           │
│         └────────────────┼───────────────────┘           │
│                          │                               │
│                 ┌────────┴────────┐                      │
│                 │    ERPNext      │                      │
│                 │  (All-in-One)   │                      │
│                 │  - Web Server   │                      │
│                 │  - Workers      │                      │
│                 │  - Scheduler    │                      │
│                 └────────┬────────┘                      │
│                          │                               │
└──────────────────────────┼───────────────────────────────┘
                           │ Port 8080
                    ┌──────┴──────┐
                    │  Browser    │
                    │  localhost  │
                    └─────────────┘
```

---

**Version:** 1.0.0  
**ERPNext:** v15  
**Last Updated:** June 2025
