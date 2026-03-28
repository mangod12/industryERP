# KBSteel ERP — AI Primer

> Read this first. It tells you everything you need to orient yourself in 60 seconds.

## What Is This?
A **steel fabrication ERP** for Kumar Brothers. Tracks raw materials, production stages, scrap, and dispatch. Built with **FastAPI + vanilla JS + SQLite**.

## How To Run
```bash
# Backend (port 8000)
cd backend_core && python -m uvicorn app.main:app --reload --port 8000

# Frontend (port 5500)
cd kumar_frontend && python -m http.server 5500

# Login: admin / Admin@123 (Boss role)
```

## The 5-Minute Mental Model

```
Excel Upload → Production Items → Fabrication → [AUTO-DEDUCT MATERIALS] → Painting → Dispatch → Done
                                                         ↓
                                                   Scrap/Reusable tracking
```

**Two systems coexist:**
- **v1** (simple): Inventory as quantities, basic stage tracking, immediate deduction
- **v2** (proper): Lot-level traceability, GRN/dispatch documents, weight precision, audit trail

## Where Things Live
| Need to change... | Look at... |
|-------------------|-----------|
| Auth/login | auth.py, security.py, deps.py |
| Customer/project CRUD | customers.py |
| Stage tracking | tracking.py (v1), tracking_api.py (v2) |
| Inventory management | inventory.py (v1), routers/inventory_v2.py (v2) |
| Excel import | excel.py |
| Scrap/reusable | scrap.py (WARNING: 746 lines) |
| GRN inward | routers/grn.py |
| Dispatch outward | routers/dispatch.py |
| Business logic | services/inventory_service.py |
| Data models | models.py (v1), models_v2.py (v2) |
| API schemas | schemas.py |
| Frontend auth/API util | js/config.js |
| Frontend CRUD/UI | js/main.js |
| Dashboard | dashboard.py (backend), index.html (frontend) |

## Danger Zones
- **scrap.py** — massive file, easy to break analytics
- **excel.py** — 90+ column aliases, fragile matching logic
- **tracking.py** — auto-deduction on stage complete, double-deduction prevention critical
- **models.py vs models_v2.py** — both share same DB Base, be careful with table conflicts

## Context Files
- `.ai/CONTEXT.md` — full architecture map, data models, change log (UPDATE THIS)
- `.ai/PRIMER.md` — this file (quick orientation)
- `.claude/projects/*/memory/` — persistent memory across sessions
