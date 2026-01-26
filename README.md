# KumarBrothers Steel ERP

A comprehensive steel fabrication inventory management system with role-based access control, GRN (Goods Receipt Note) workflow, dispatch management, and full material traceability.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Step 1: Setup Environment

```powershell
cd c:\Users\ansha\Downloads\next_project

# Create and activate virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Backend Server

```powershell
cd backend_core
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at: **http://127.0.0.1:8000**

### Step 3: Start Frontend Server

Open a new terminal:

```powershell
cd kumar_frontend
python -m http.server 5500
```

Frontend will be available at: **http://127.0.0.1:5500**

### Step 4: Access the Application

Open your browser and navigate to: **http://127.0.0.1:5500/login.html**

---

## 🔐 Test Credentials

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| `admin` | `Admin@123` | Boss | Full access to all features |

### Creating Additional Test Users

After logging in as admin, you can create users with different roles:

| Role | Description |
|------|-------------|
| **Boss** | Full system access |
| **Software Supervisor** | Inventory, GRN, Dispatch management |
| **Store Keeper** | Stock operations, GRN creation |
| **QA Inspector** | Quality inspection and approval |
| **Dispatch Operator** | Dispatch operations only |
| **User** | View-only access |

---

## 📱 Available Pages

| Page | URL | Description |
|------|-----|-------------|
| Login | `/login.html` | User authentication |
| Dashboard | `/index.html` | Overview and stats |
| Materials | `/materials.html` | Material master catalog |
| Stock | `/stock.html` | Stock lots with heat traceability |
| GRN | `/grn.html` | Goods Receipt Notes workflow |
| Dispatch | `/dispatch.html` | Outward dispatch management |
| Customers | `/customers.html` | Customer management |
| Settings | `/settings.html` | System settings |

---

## 🔧 API Documentation

Once the backend is running, access the interactive API docs:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /auth/login` | User authentication |
| `GET /api/v2/inventory/materials` | List all materials |
| `GET /api/v2/inventory/stock` | List stock lots |
| `POST /api/v2/grn/` | Create new GRN |
| `GET /api/v2/grn/vendors` | List vendors |
| `POST /api/v2/dispatch/` | Create dispatch note |

---

## 🏗️ Project Structure

```
next_project/
├── backend_core/           # FastAPI Backend
│   ├── app/
│   │   ├── main.py         # App entry point
│   │   ├── models.py       # V1 database models
│   │   ├── models_v2.py    # V2 steel industry models
│   │   ├── security.py     # Authentication & RBAC
│   │   ├── deps.py         # Dependencies
│   │   ├── routers/        # API routers
│   │   │   ├── grn.py      # GRN endpoints
│   │   │   ├── dispatch.py # Dispatch endpoints
│   │   │   └── inventory_v2.py
│   │   └── services/       # Business logic
│   └── data/
│       └── kumar_core.db   # SQLite database
│
├── kumar_frontend/         # Frontend (HTML/JS/CSS)
│   ├── index.html          # Dashboard
│   ├── login.html          # Login page
│   ├── grn.html            # GRN management
│   ├── dispatch.html       # Dispatch management
│   ├── materials.html      # Materials master
│   ├── stock.html          # Stock inventory
│   ├── js/
│   │   ├── config.js       # API config & auth
│   │   └── main.js         # Main application JS
│   └── css/
│       └── main.css        # Styles
│
├── scripts/
│   └── create_admin.py     # Admin user creation script
│
└── requirements.txt        # Python dependencies
```

---

## 🔄 Testing Workflow

### 1. Login Test
```
1. Navigate to http://127.0.0.1:5500/login.html
2. Enter: admin / Admin@123
3. Click Login
4. Should redirect to Dashboard
```

### 2. Create Material Test
```
1. Go to Materials page
2. Click "+ Add Material"
3. Fill in:
   - Code: STL-CR-1.5
   - Name: CR Steel Sheet 1.5mm
   - Type: sheet
   - Grade: IS 513 CR2
   - Thickness: 1.5
4. Click Save
```

### 3. Create Vendor & GRN Test
```
1. Go to GRN page
2. Click "New GRN"
3. Select vendor (Tata Steel already exists)
4. Fill vehicle number, driver details
5. Click "Create GRN"
6. Add line items with heat numbers
7. Submit for QA
```

### 4. Dispatch Test
```
1. Go to Dispatch page
2. Click "New Dispatch"
3. Select customer
4. Pick stock lots (FIFO)
5. Confirm dispatch
```

---

## ⚙️ Environment Variables (Production)

For production deployment, set these environment variables:

```powershell
$env:KUMAR_SECRET_KEY = "your-secure-64-char-secret-key"
$env:ENVIRONMENT = "production"
$env:CORS_ORIGINS = "https://yourdomain.com"
$env:DATABASE_URL = "postgresql://user:pass@host/db"  # Optional
```

---

## 📝 Notes

- Default database: SQLite (stored in `backend_core/data/kumar_core.db`)
- All weights stored internally in KG, displayed in MT where appropriate
- Heat number tracking for full steel traceability
- FIFO picking for dispatch operations

---

## 🐛 Troubleshooting

### Port already in use
```powershell
# Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database reset
```powershell
# Delete database and restart server (will recreate tables)
Remove-Item backend_core/data/kumar_core.db
# Restart backend server
# Run create_admin.py to create admin user again
```

### Create admin user manually
```powershell
$env:PYTHONPATH = "c:\Users\ansha\Downloads\next_project"
python scripts/create_admin.py --username admin --email admin@kumarbrothers.com --password Admin@123
```
