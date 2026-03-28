# AI Context — KBSteel ERP

> Auto-maintained by Claude. This file tracks what's where, what changed, and what to watch out for.
> **Last updated:** 2026-03-28

---

## Architecture Map

```
kbsteel-old/
├── backend_core/app/           # FastAPI backend (Python 3.11+)
│   ├── main.py                 # App factory, router registration, startup
│   ├── db.py                   # SQLAlchemy engine, session, Base
│   ├── models.py               # v1 ORM models (15 tables)
│   ├── models_v2.py            # v2 ORM models (12 tables, enums, constraints)
│   ├── schemas.py              # Pydantic v2 request/response schemas
│   ├── security.py             # JWT, bcrypt, RBAC, password policy
│   ├── deps.py                 # DI: get_db, get_current_user, require_role
│   ├── auth.py                 # POST /auth/login, /auth/register
│   ├── customers.py            # CRUD /customers, /customers/{id}/items
│   ├── tracking.py             # Stage progression v1 (fabrication→painting→dispatch)
│   ├── tracking_api.py         # Stage progression v2 with FIFO + checklists
│   ├── inventory.py            # v1 inventory CRUD + stats
│   ├── excel.py                # Excel/CSV import with 90+ column aliases
│   ├── dashboard.py            # GET /dashboard/summary
│   ├── scrap.py                # Scrap + reusable stock + analytics (746 lines!)
│   ├── notifications.py        # In-app notifications + settings
│   ├── queries.py              # Quality issue tracking
│   ├── instructions.py         # Boss→user instructions
│   ├── users.py                # Profile + password change
│   ├── routers/
│   │   ├── inventory_v2.py     # v2: MaterialMaster, StockLot, movements
│   │   ├── grn.py              # v2: Goods Receipt Notes + vendors
│   │   └── dispatch.py         # v2: Outward dispatch workflow
│   └── services/
│       └── inventory_service.py # Business logic: FIFO, sequences, weight math
├── kumar_frontend/             # Static frontend (vanilla JS + Bootstrap 5)
│   ├── js/config.js            # KBConfig, KBAuth, KBApi, KBUI utilities
│   ├── js/main.js              # CRUD logic, forms, dashboard loading
│   ├── css/main.css            # Styles
│   └── *.html                  # 22 HTML pages (see Page Map below)
├── scripts/
│   ├── create_admin.py         # Bootstrap Boss user
│   ├── migrate_db.py           # DB init
│   └── migrate_v2.py           # v1→v2 data migration
├── tools/
│   ├── change_role.py          # Admin: change user role
│   ├── inspect_user.py         # Admin: view user
│   └── smoke_test.py           # Login test
└── requirements.txt            # fastapi, sqlalchemy, pandas, jose, bcrypt
```

---

## Data Model Summary

### v1 Tables (models.py) — Active Production
| Table | Purpose | Key Relations |
|-------|---------|---------------|
| users | Auth + RBAC | — |
| customers | Projects/clients | → production_items |
| production_items | Tracking items from Excel | → customer, → stages |
| stage_tracking | Per-stage status | → production_item |
| inventory | Raw material stock (Float) | — |
| material_usage | Deduction records | → customer, → production_item |
| material_consumption | FIFO consumption log | → material_usage, → inventory |
| queries | Quality issues | → customer |
| instructions | Boss messages | → user |
| notifications | In-app alerts | → user |
| notification_settings | Per-user prefs | → user |
| role_notification_settings | Role defaults | — |
| tracking_stage_history | Stage audit trail | → production_item |
| scrap_records | Waste tracking | → production_item, → customer |
| reusable_stock | Reusable offcuts | → production_item, → customer |

### v2 Tables (models_v2.py) — Improved Traceability
| Table | Purpose | Key Relations |
|-------|---------|---------------|
| material_master | Material catalog | → stock_lots |
| vendors | Supplier data | → grns, → stock_lots |
| storage_locations | Yard/warehouse (hierarchical) | → stock_lots |
| stock_lots | Individual lot/batch (Decimal weight) | → material, → vendor, → grn, → movements |
| stock_movements | Immutable audit log | → stock_lot |
| goods_receipt_notes | Inward documents | → vendor, → line_items, → stock_lots |
| grn_line_items | GRN details | → grn, → material |
| dispatch_notes | Outward documents | → customer, → line_items |
| dispatch_line_items | Dispatch details | → dispatch, → stock_lot |
| production_items_v2 | Enhanced production | → stages, → consumption |
| stage_tracking_v2 | Enhanced stages | → production_item |
| material_consumption_v2 | Lot-level consumption | → production_item, → stock_lot |
| audit_logs | General audit | → user |
| system_config | Key-value settings | — |
| number_sequences | Auto-incrementing doc numbers | — |

---

## Page Map (Frontend)

| Page | File | Key API Dependencies |
|------|------|---------------------|
| Login | login.html | POST /auth/login |
| Dashboard | index.html | GET /dashboard/summary, GET /scrap/summary |
| Raw Materials | raw_material.html | GET/POST/PUT/DELETE /inventory |
| Customers | customers.html | GET/POST /customers |
| Add Customer | customer_add.html | POST /customers |
| Edit Customer | customer_edit.html | PUT /customers/{id} |
| Customer Details | customer_details.html | GET /customers/{id} |
| Tracking v1 | tracking.html | GET /tracking/customers, POST /tracking/start-stage, /complete-stage |
| Tracking v2 | tracking_v2.html | GET/PUT /api/tracking |
| Materials (v2) | materials.html | GET/POST /api/v2/inventory/materials |
| Stock (v2) | stock.html | GET /api/v2/inventory/lots |
| GRN | grn.html | GET/POST /api/v2/grn |
| Dispatch | dispatch.html | GET/POST /api/v2/dispatch |
| Scrap | scrap.html | GET/POST /scrap/records, GET /scrap/analytics |
| Reusable | reusable.html | GET/POST /scrap/reusable |
| Queries | queries.html | GET/POST /queries |
| Instructions | instructions.html | GET /instructions |
| Instructions Edit | instructions_edit.html | POST /instructions |
| Settings | settings.html | (local config) |
| Account | account-settings.html | GET /users/me, POST /users/change-password |
| Notifications | notification-settings.html | GET/PUT /notifications/settings |
| Register | register.html | POST /auth/register |

---

## RBAC Matrix

| Role | Create | Read | Update | Delete | Special |
|------|--------|------|--------|--------|---------|
| Boss | All | All | All | All | Register users, instructions |
| Software Supervisor | Inv, GRN, Dispatch | All | Inv, Production | — | Approve GRN/Dispatch |
| Store Keeper | Inv, GRN | All | Inv, Production | — | — |
| QA Inspector | — | All | QA status | — | Approve/reject/hold |
| Dispatch Operator | Dispatch | All | Dispatch | — | — |
| User | — | All | — | — | Read-only |

---

## Change Log

| Date | What Changed | Files | Why |
|------|-------------|-------|-----|
| 2026-03-28 | Initial AI context created | .ai/CONTEXT.md | Baseline mapping |

---

## Active Concerns

1. **scrap.py at 746 lines** — needs decomposition into service + router
2. **No test coverage** — only smoke_test.py
3. **v1↔v2 migration incomplete** — migrate_v2.py exists but unclear status
4. **SQLite limitations** — SELECT FOR UPDATE not supported, race conditions possible
5. **Hardcoded values** — scrap loss at 50/kg, low-stock threshold at 15%
6. **Duplicate deduction flags** — fabrication_deducted vs material_deducted on ProductionItem

---

## Self-Improvement Protocol

After each session that modifies code:
1. Update the **Change Log** section above with date, files, and reason
2. If new endpoints added → update **Page Map** or architecture
3. If new models/tables added → update **Data Model Summary**
4. If issues discovered → add to **Active Concerns**
5. If issues resolved → move to Change Log with resolution note
6. Update memory files in `.claude/projects/*/memory/` if new project-level insights emerge
