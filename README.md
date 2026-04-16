# KumarBrothers Steel ERP
(PRODUCTION READY)

A comprehensive steel fabrication tracking and inventory management system with automatic material deduction, Excel import, and real-time dashboard.

---

## 📋 System Workflow

### Overview Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KUMARBROTHERS STEEL ERP WORKFLOW                      │
└─────────────────────────────────────────────────────────────────────────────┘

    STEP 1                    STEP 2                    STEP 3
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│  Add Raw    │          │ Add Customer│          │Upload Excel │
│  Materials  │    →     │  /Project   │    →     │  Tracking   │
│  (Profiles) │          │             │          │    File     │
└─────────────┘          └─────────────┘          └─────────────┘
      │                                                  │
      │                                                  ▼
      │                                    ┌──────────────────────────┐
      │                                    │ System Auto-Links        │
      │                                    │ PROFILE → Raw Material   │
      │                                    │ (e.g., UB203X133X25)     │
      └───────────────────────────────────►└──────────────────────────┘
                                                         │
                                                         ▼
                         TRACKING STAGES (Sequential - Cannot Skip)
    ┌─────────────────┬─────────────────┬─────────────────┐
    │  FABRICATION    │    PAINTING     │    DISPATCH     │
    │    (Stage 1)    │    (Stage 2)    │    (Stage 3)    │
    │                 │                 │                 │
    │  ✓ Complete     │  ✓ Complete     │  ✓ Complete     │
    │      ↓          │      ↓          │      ↓          │
    │  AUTO-DEDUCT    │  Move to next   │    FINISHED!    │
    │  from inventory │     stage       │                 │
    └─────────────────┴─────────────────┴─────────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────┐
                                          │  Dashboard Updates       │
                                          │  - Stock reduced         │
                                          │  - Progress shown        │
                                          │  - All users see changes │
                                          └──────────────────────────┘
```

---

## 🔄 Core Features

### 1. Robust Tracking Architecture
*   **Separation of Concerns**: Visibility logic is handled by optimized API endpoints (`/tracking/all-items`), preventing "N+1 query" lag even with thousands of items.
*   **Transactional Production**: Stage transitions (Fabrication → Painting → Dispatch) are handled by a dedicated `TrackingService`, ensuring data integrity and correct inventory deduction.
*   **Checklists**: Each tracking item has a checklist (e.g., "Cut", "Weld", "Clean") that must be completed before the stage moves forward.

### 2. Role-Based Access Control (RBAC)
*   **Boss**: Full system access. Can create users, manage inventory, and override checks.
*   **Software Supervisor**: Can manage inventory, production, and users (limited).
*   **Store Keeper / QA / Dispatch**: Role-specific access.
*   **Security**: Registration is restricted. Only **Boss** and **Software Supervisor** can create new accounts.

### 3. Automatic Excel Import
*   Upload client Excel files directly.
*   Auto-detects columns: `Drawing no`, `PROFILE`, `QTY.`, `WT-(kg)`, `PAINT`, etc.
*   Auto-links `PROFILE` column to your Inventory (Raw Materials).

### 4. Real-Time Dashboard
*   Auto-refreshes every 10 seconds.
*   Shows live counts for Fabrication, Painting, and Dispatch.
*   Monitors Raw Material stock and alerts on Low Stock (<15%).

### 5. Notification Preferences
*   Users can customize which notifications they receive in **Settings**.
*   Categories include: Instructions from Boss, Stage Changes, Query Status, Low Stock Alerts, and Dispatch Completion.
*   Filter logic is handled on the backend to reduce noise.

---

## 🚀 Quick Start (Production)

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Step 1: Setup Environment

```powershell
# 1. Open Terminal in project root

# 2. Create virtual environment
python -m venv .venv

# 3. Activate usage
.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Backend Server

```powershell
cd backend_core
python -m uvicorn app.main:app --reload --port 8000
```
*Backend is now running at: **http://127.0.0.1:8000***

### Step 3: Start Frontend Server

Open a **new** terminal window:

```powershell
cd kumar_frontend
python -m http.server 5500
```
*Frontend is now running at: **http://127.0.0.1:5500***

### Step 4: Login

Go to **http://127.0.0.1:5500/login.html**

**Standard Admin Credentials:**
*   Username: `admin` (or `Boss`)
*   Password: *(Randomized on first run for securityized. Check console logs or use your set password)*

---

## 📱 User Guide

### 1. How to Register New Users
> **Restricted**: Only "Boss" or "Software Supervisor" can do this.
1.  Log in as Admin (Boss).
2.  Navigate to `register.html` (or click "Register" if visible in settings).
3.  Fill in details. **Note**: You cannot create an account with higher privileges than your own (Supervisor cannot create Boss).

### 2. How to Upload Excel
1.  Go to **Customers** page.
2.  Add a Customer (e.g., "ABC Corp").
3.  Click **"Upload Excel"**.
4.  Select your file. The system will preview raw material matches.
5.  Click **Import**.

### 3. How to Track Production
1.  Go to **Tracking** page.
2.  Use the **Kanban Board** to visualize flow.
3.  Click item to view **Checklist**.
4.  Check all items → Click **"Complete Fabrication"**.
5.  *System auto-deducts material and moves item to Painting.*

### 4. Notification Settings
1.  Click your username (top right) → **Settings**.
2.  Navigate to **Notification Preferences**.
3.  Toggle categories on/off and click **Save Preferences**.

---

## 🔧 Technical Notes for Developers

### Split-Brain Routing (Legacy vs New)
*   **GET /tracking/all-items**: Optimized read endpoint for the Frontend table/board.
*   **PUT /api/tracking/{id}**: New `TrackingService` endpoint for writing state changes.

### Database
*   Type: SQLite
*   Path: `backend_core/data/kumar_core.db`
*   **Resetting**: To wipe data, stop the backend, delete this file, and restart.

### Key Files
*   `backend_core/app/services/tracking_service.py`: Core logic for stage transitions.
*   `backend_core/app/auth.py`: Login and Registration logic.
*   `kumar_frontend/tracking_v2.js`: Frontend logic for Kanban and Pagination.

---

## 📞 Support
For issues or questions, contact the development team.
