# KBSteel ERP - Quick Primer

> Read this first. 60-second orientation for any AI agent or developer.

## What Is This?
**KumarBrothers Steel Industry ERP** — a production tracking and inventory management system for a real steel fabrication plant. Tracks raw materials from receipt through fabrication, painting, dispatch, and scrap recovery.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.128.0, Python 3.11+ |
| ORM | SQLAlchemy 2.0.46, Pydantic v2 |
| Database | SQLite (dev), PostgreSQL (prod) |
| Frontend | Vanilla JS, Bootstrap 5.3.2, no build step |
| Auth | JWT (python-jose), bcrypt, 6 RBAC roles |
| Excel | pandas 3.0.0 + openpyxl for import/export |
| Deploy | Railway.app / Heroku, Gunicorn + Uvicorn |

## Directory Layout
```
kbsteel-old/
├── backend_core/app/          # FastAPI application (9,923 lines)
│   ├── main.py                # App factory, router mounting
│   ├── models.py              # v1 models (15 tables)
│   ├── models_v2.py           # v2 models (12 tables)
│   ├── schemas.py             # Pydantic schemas
│   ├── security.py            # JWT, RBAC, rate limiting
│   ├── db.py                  # Engine, session, admin seed
│   ├── services/              # Business logic layer
│   │   ├── inventory_service.py   # Stock lot ops, weight conversion
│   │   ├── tracking_service.py    # Stage flow, material deduction
│   │   ├── production_service.py  # Excel import, fuzzy matching
│   │   └── customer_service.py    # Customer CRUD
│   └── routers/               # v2 API endpoints
│       ├── inventory_v2.py    # Stock lots, movements, reconciliation
│       ├── grn.py             # Goods receipt workflow
│       └── dispatch.py        # Dispatch workflow
├── kumar_frontend/            # 24 HTML pages, 3 JS files
│   ├── js/config.js           # Auth, API client, RBAC
│   ├── js/main.js             # Global UI, notifications
│   └── css/main.css           # Theming
├── deploy/                    # start.sh, nginx.conf
├── tests/                     # Empty (only structure)
└── docs/                      # ARCHITECTURE_REVIEW.md
```

## Core Business Flow
```
Raw Material Receipt (GRN) → Weighbridge → QA Inspection → Stock Lot
     ↓
Customer Order → Excel Upload (auto-link profiles to inventory)
     ↓
Fabrication → Painting → Dispatch → Completed
     ↓                              ↓
Auto-deduct inventory          Create dispatch note → Weighbridge → Ship
     ↓
Scrap/Waste → Recovery or Write-off
```

## Dual Architecture (v1 + v2)
- **v1 (legacy, active):** Simple inventory + stage tracking. Endpoints at `/auth`, `/customers`, `/tracking`, `/inventory`, etc.
- **v2 (improved, coexisting):** Lot-level traceability, GRN/dispatch workflows, immutable audit trail via StockMovement. Endpoints at `/api/v2/*`.
- Both share the same database. New features should prefer v2 patterns.

## 6 User Roles
1. **Boss** — full access (25 permissions)
2. **Software Supervisor** — all except user delete, settings update
3. **Store Keeper** — inventory, GRN, dispatch, production, reports
4. **QA Inspector** — QA approval/rejection, inventory view, reports
5. **Dispatch Operator** — dispatch ops, production view, reports
6. **User** — view-only

## Key Numbers
- **104 API endpoints** (77 v1 + 27 v2)
- **27 database tables** (15 v1 + 12 v2)
- **9,923 lines** backend code across 33 Python files
- **24 HTML pages**, 3 JS files (~1,700 lines frontend JS)

## Danger Zones
- `scrap.py` (745 lines) — needs decomposition
- `excel.py` (451 lines) — 90+ column aliases, fragile matching
- `tracking.py` (761 lines) — auto-deduction logic, double-deduction prevention critical
- v1 & v2 models share same Base — table conflict risk
- No tests (empty test directories)
- No CI/CD pipeline
- Alembic migrations incomplete
