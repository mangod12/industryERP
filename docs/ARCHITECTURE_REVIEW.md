# Steel Industry Inventory Management System
## Architecture Review & Improvement Documentation

### Executive Summary

This document provides a comprehensive architectural review of the Kumar Brothers Steel Industry Inventory Management System. It identifies critical issues, provides fixes, and proposes an improved architecture suitable for real industrial deployment.

---

## 🔴 Critical Issues Identified

### 1. Data Model Issues (SEVERITY: CRITICAL)

| Issue | Impact | Fix |
|-------|--------|-----|
| Integer weight columns | Loss of precision (2.5 tons → 2 tons = 500kg loss!) | Use `Numeric(15,3)` for all weights |
| No heat/lot traceability | Legal non-compliance, no recall capability | Added `StockLot` model with full traceability |
| No audit trail | Cannot track who changed what, when | Added `StockMovement` immutable log |
| Missing gross/tare/net weights | Cannot reconcile with weighbridge | Added proper weight breakdown |

### 2. Security Issues (SEVERITY: CRITICAL)

| Issue | Impact | Status | Fix |
|-------|--------|--------|-----|
| Hardcoded secret key | Auth bypass | **RESOLVED** | Environment-based key with validation |
| No password policy | Weak passwords | **RESOLVED** | Min 8 chars, hashed securely |
| Missing rate limiting | Brute force | **RESOLVED** | Added RateLimiter middleware |
| Coarse RBAC | No permissions | **RESOLVED** | Added permission-based checks |

### 3. Business Logic Issues (SEVERITY: HIGH)

| Issue | Impact | Fix |
|-------|--------|-----|
| Race conditions in updates | Stock counts can go negative | Row-level locking with `FOR UPDATE` |
| No transaction safety | Partial failures leave inconsistent state | Proper transaction boundaries |
| Missing FIFO support | Stock aging issues | Added FIFO picking algorithm |
| No GRN/Dispatch workflow | Incomplete inward/outward process | Added complete document workflows |

---

## 📁 New File Structure

```
backend_core/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── db.py                      # Database configuration
│   ├── models.py                  # SQLAlchemy models (Added 'category' to Notification)
│   ├── schemas.py                 # Pydantic schemas (Updated for filter support)
│   ├── security.py                # Security module (Hashing, JWT, Rate Limiting)
│   ├── auth.py                    # Login/Register endpoints
│   ├── deps.py                    # Dependencies (Auth/DB)
│   ├── services/                  
│   │   └── tracking_service.py    # Core business logic for stage transitions
│   ├── notifications.py           # Notification API with Category filtering
│   ├── tracking.py                # Tracking API endpoints
│   ├── inventory.py               # Inventory management
│   ├── queries.py                 # Query system
│   └── instructions.py            # Boss instructions system
```

---

## 🏗️ Recommended Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Web UI    │  │  Mobile App │  │  API Clients│              │
│  │  (Vue/React)│  │ (Flutter)   │  │ (ERP/SAP)   │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              FastAPI Application (main.py)               │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │Inventory │ │   GRN    │ │ Dispatch │ │ Tracking │   │    │
│  │  │  Router  │ │  Router  │ │  Router  │ │  Router  │   │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │    │
│  └───────┼────────────┼────────────┼────────────┼──────────┘    │
│          │            │            │            │                │
│  ┌───────▼────────────▼────────────▼────────────▼──────────┐    │
│  │               SECURITY MIDDLEWARE                        │    │
│  │   Authentication │ Authorization │ Rate Limiting         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Business Logic Services                     │    │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │    │
│  │  │ StockLot     │  │   GRN       │  │  Inventory   │   │    │
│  │  │  Service     │  │  Service    │  │   Query      │   │    │
│  │  │              │  │             │  │   Service    │   │    │
│  │  │ • consume()  │  │ • create()  │  │              │   │    │
│  │  │ • adjust()   │  │ • approve() │  │ • summary()  │   │    │
│  │  │ • split()    │  │ • add_line()│  │ • aging()    │   │    │
│  │  │ • transfer() │  │             │  │ • fifo_pick()│   │    │
│  │  └──────────────┘  └─────────────┘  └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  SQLAlchemy ORM                          │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐          │    │
│  │  │ StockLot   │ │ Movement   │ │   GRN      │          │    │
│  │  │            │ │            │ │            │          │    │
│  │  └────────────┘ └────────────┘ └────────────┘          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               PostgreSQL / SQLite                        │    │
│  │                                                          │    │
│  │   stock_lots │ stock_movements │ grn │ dispatch │ ...   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Improved Data Model (Entity Relationship)

```
┌─────────────────┐       ┌─────────────────┐
│  MaterialMaster │       │     Vendor      │
│─────────────────│       │─────────────────│
│ id              │       │ id              │
│ code (unique)   │       │ code            │
│ name            │       │ name            │
│ material_type   │       │ gstin           │
│ grade           │       │ address         │
│ thickness_mm    │       └────────┬────────┘
│ width_mm        │                │
│ reorder_level   │                │
└────────┬────────┘                │
         │                         │
         │ 1:N                     │ 1:N
         ▼                         ▼
┌─────────────────────────────────────────────┐
│                 StockLot                     │
│─────────────────────────────────────────────│
│ id                                          │
│ lot_number (unique)                         │
│ material_id ────────────────────────────────┼─→ MaterialMaster
│ vendor_id ──────────────────────────────────┼─→ Vendor
│ grn_id ─────────────────────────────────────┼─→ GoodsReceiptNote
│ location_id ────────────────────────────────┼─→ StorageLocation
│                                             │
│ ★ TRACEABILITY                              │
│ heat_number                                 │
│ batch_number                                │
│ coil_number                                 │
│                                             │
│ ★ WEIGHT (all in KG, Decimal precision)    │
│ gross_weight_kg                             │
│ tare_weight_kg                              │
│ net_weight_kg                               │
│ current_weight_kg                           │
│                                             │
│ ★ QUALITY                                   │
│ qa_status (pending/approved/rejected/hold)  │
│ test_certificate_ref                        │
│                                             │
│ ★ STATUS                                    │
│ is_active                                   │
│ is_blocked                                  │
│ received_date                               │
└─────────────────────────────────────────────┘
         │
         │ 1:N (IMMUTABLE AUDIT TRAIL)
         ▼
┌─────────────────────────────────────────────┐
│              StockMovement                   │
│─────────────────────────────────────────────│
│ id                                          │
│ movement_number (unique)                    │
│ stock_lot_id                                │
│ movement_type (enum)                        │
│   • INWARD_PURCHASE                         │
│   • CONSUMPTION                             │
│   • ADJUSTMENT_PLUS/MINUS                   │
│   • SPLIT / MERGE                           │
│   • TRANSFER                                │
│                                             │
│ weight_change_kg (+ for in, - for out)     │
│ weight_before_kg                            │
│ weight_after_kg                             │
│                                             │
│ reference_type (grn/dispatch/adjustment)    │
│ reference_id                                │
│                                             │
│ created_by ─────────────────────────────────┼─→ User
│ movement_date                               │
│ is_reversed                                 │
└─────────────────────────────────────────────┘
```

---

## 🔐 Security Architecture

### Permission-Based Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│                         PERMISSIONS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INVENTORY          GRN              DISPATCH          QA       │
│  ────────────       ────────         ────────────      ────     │
│  • view             • view           • view            • view   │
│  • create           • create         • create          • inspect│
│  • update           • approve        • approve         • approve│
│  • delete                                              • reject │
│  • adjust                                              • hold   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           ROLES                                  │
├──────────────┬─────────────────────────────────────────────────-┤
│    Boss      │ ALL PERMISSIONS                                  │
├──────────────┼──────────────────────────────────────────────────┤
│  Software    │ inventory:*, grn:*, dispatch:*, report:*         │
│  Supervisor  │                                                  │
├──────────────┼──────────────────────────────────────────────────┤
│ Store Keeper │ inventory:view/create/update, grn:view/create    │
│              │ dispatch:view/create, production:consume         │
├──────────────┼──────────────────────────────────────────────────┤
│ QA Inspector │ inventory:view, grn:view, qa:*                   │
├──────────────┼──────────────────────────────────────────────────┤
│   Dispatch   │ inventory:view, dispatch:view/create             │
│   Operator   │                                                  │
├──────────────┼──────────────────────────────────────────────────┤
│     User     │ view-only access                                 │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## 🔄 Workflow Diagrams

### GRN (Goods Receipt Note) Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Gate Entry  │────►│  Weighbridge │────►│    Store     │
│              │     │              │     │   Receipt    │
│  • Vehicle   │     │  • Gross wt  │     │              │
│  • Driver    │     │  • Tare wt   │     │  • Verify    │
│  • Invoice   │     │  • Net wt    │     │    qty/wt    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │     DRAFT          │    DRAFT           │   SUBMITTED
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                          GRN                                 │
│  Status: DRAFT → SUBMITTED → APPROVED                       │
└─────────────────────────────────────────────────────────────┘
                                                      │
                              ┌──────────────┐       │
                              │      QA      │◄──────┘
                              │  Inspection  │
                              │              │
                              │ • Approved   │
                              │ • Rejected   │
                              │ • On Hold    │
                              └──────┬───────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │   Approve    │
                              │     GRN      │
                              │              │
                              │ Creates:     │
                              │ • StockLots  │
                              │ • Movements  │
                              └──────────────┘
```

### Dispatch Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Create     │────►│    Pick      │────►│  Weighbridge │
│   Dispatch   │     │   Material   │     │  Verification│
│              │     │              │     │              │
│  • Customer  │     │  • FIFO      │     │  • Gross wt  │
│  • Vehicle   │     │  • By lot    │     │  • Variance  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │     DRAFT          │    DRAFT           │   SUBMITTED
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                       DISPATCH                               │
│  Status: DRAFT → SUBMITTED → APPROVED                       │
└─────────────────────────────────────────────────────────────┘
                                                      │
                              ┌──────────────┐       │
                              │   Approve    │◄──────┘
                              │   Dispatch   │
                              │              │
                              │ • Deduct     │
                              │   stock      │
                              │ • Create     │
                              │   movements  │
                              └──────────────┘
```

---

## 📋 Migration Guide

### Step 1: Database Migration

```python
# Run migrations to add new tables
# Keep existing tables for backward compatibility

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create new tables
    op.create_table('material_master', ...)
    op.create_table('vendors', ...)
    op.create_table('storage_locations', ...)
    op.create_table('stock_lots', ...)
    op.create_table('stock_movements', ...)
    op.create_table('goods_receipt_notes', ...)
    op.create_table('dispatch_notes', ...)
    
    # Migrate existing inventory data
    # ... data migration logic ...
```

### Step 2: Register New Routers

```python
# main.py
from .routers import inventory_v2, grn, dispatch

app.include_router(inventory_v2.router)
app.include_router(grn.router)
app.include_router(dispatch.router)
```

### Step 3: Environment Configuration

```bash
# .env file
KUMAR_SECRET_KEY=your-64-char-secret-key-here
ENVIRONMENT=production
TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql://user:pass@localhost/kumarbrothers
```

---

## 🚀 Recommended Improvements (Future)

1. **Background Jobs**
   - Low stock alerts (email/SMS)
   - Stock aging reports (daily)
   - Movement reconciliation

2. **Integration APIs**
   - SAP/ERP integration endpoints
   - Tally export format
   - Weighbridge device integration

3. **Performance**
   - Redis caching for stock summaries
   - Database read replicas
   - Archival of old movements

4. **Features**
   - Barcode/RFID scanning
   - Mobile app for store operations
   - Dashboard with real-time metrics

---

## 📝 Files Created/Modified

- [models.py](backend_core/app/models.py) - Added Notification categories
- [security.py](backend_core/app/security.py) - Secured with RateLimiting
- [services/tracking_service.py](backend_core/app/services/tracking_service.py) - Centralized stage tracking
- [notifications.py](backend_core/app/notifications.py) - Category-based filtering
- [notification-settings.html](kumar_frontend/notification-settings.html) - Robust API/Auth handling

### Files Fixed:
- [deps.py](backend_core/app/deps.py) - Removed hardcoded secret key
- [inventory.py](backend_core/app/inventory.py) - Added validation and transaction safety

---

**Document Version:** 1.2  
**Review Date:** February 16, 2026  
**Reviewer:** Kumar Brothers Dev Team
