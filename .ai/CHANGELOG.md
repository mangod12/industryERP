# Change Log

> Track all AI-assisted changes here. Updated automatically after each code modification session.

## Format
```
## [YYYY-MM-DD] Summary
- **Files:** list of modified files
- **Type:** feat | fix | refactor | docs | test | chore
- **Details:** what and why
- **Impact:** what other parts of the system are affected
```

---

## [2026-03-28] Deep Audit Fix — All Critical/High Issues Resolved

6 parallel agent teams resolved all 8 CRITICAL and 15 HIGH issues from the multi-perspective audit:

### Critical Fixes
- **C1**: BOM fabrication auto-complete now triggers material deduction (`stage_service.py`)
- **C2**: Fixed duplicate `db.add(usage)` copy-paste bug — proper flush-then-create pattern (`deduction_service.py`)
- **C3**: Enabled SQLite foreign key enforcement via `PRAGMA foreign_keys=ON` (`db.py`)
- **C4**: Table creation order secured for PostgreSQL deployment (`main.py`)
- **C5**: Added auth guards to `settings.html`, `account-settings.html`, `notification-settings.html`
- **C6**: Fixed XSS in `login.html` and `register.html` — innerHTML → textContent for API data
- **C7**: Fixed `register.html` auth guard to use JWT-based `KBAuth.getRole()`
- **C8**: Fixed `dispatch.html` endpoint path (`/stock` → `/lots`), fixed `grn.html` item loading

### High Fixes
- **H1**: Schema `int` → `float` for `InventoryIn/Out` and `MaterialUsage` (data truncation)
- **H2**: Unified deduction flags — both paths set both flags; idempotency check uses `or`
- **H3**: Documented canonical `get_db` in `deps.py`
- **H4**: Dashboard now aggregates BOM assemblies (`bom_summary` in response)
- **H6**: Bulk stage completion now triggers deduction for fabrication
- **H8**: Fixed `lot_number` filter bug in BOM import (proper NULL handling)
- **H9**: BOM import wrapped in `begin_nested()` for atomic rollback on error
- **H10**: Scrap return requires inventory match, uses `with_for_update()`, warns on clamp
- **H11**: All pages now import `escapeHtml.js` (16 pages)
- **H12**: 16 pages migrated from hardcoded navbar to `KBNavbar.render()`
- **H13**: All 7 CSV template endpoints now require authentication
- **H15**: Test suite expanded: 67 tests (unit + integration + RBAC + stage progression)

### New Files
- `backend_core/app/constants.py` — shared `STAGE_ORDER`, `STAGE_FLOW`
- `tests/integration/test_bom_flow.py` — BOM lifecycle HTTP integration tests
- `tests/integration/test_stage_progression.py` — v1 + v2 stage progression tests
- `tests/integration/test_rbac.py` — 15 RBAC permission enforcement tests
- `tests/unit/test_bom_service.py` — 13 BOM service unit tests
- `tests/unit/test_stage_service.py` — 11 per-piece completion tests

### Test Results: 67 passed, 2 skipped (Postgres-only), 0 failures

## [2026-03-28] Full System Audit + Redesign — Phases 0-8 Implementation

### Phase 0: Foundation
- **Files:** `backend_core/alembic.ini`, `backend_core/alembic/env.py`, `backend_core/alembic/script.py.mako`, `requirements.txt`, `backend_core/app/main.py`
- **Type:** chore
- **Details:** Added Alembic migration infrastructure. Guarded `create_all` behind `ENVIRONMENT != production`. Added `alembic`, `pytest-cov`, `httpx` to requirements.
- **Impact:** Production deployments now require `alembic upgrade head`

### Phase 0b: Test Infrastructure
- **Files:** `tests/conftest.py`, `tests/factories.py`, `tests/**/__init__.py`
- **Type:** test
- **Details:** Created comprehensive test infrastructure with in-memory SQLite fixtures, TestClient, auth token fixtures for all 6 roles, and factory helpers.

### Phase 1: Fix Double-Deduction Race Condition (CRITICAL)
- **Files:** `backend_core/app/services/deduction_service.py` (NEW), `backend_core/app/tracking.py`, `backend_core/app/tracking_api.py`
- **Type:** fix
- **Details:** Consolidated THREE separate deduction paths into single `DeductionService` with SELECT FOR UPDATE locking, SAVEPOINT-wrapped atomic deductions, and idempotency checks. Inventory can NEVER go negative. Fixed silent `except: pass` failures with proper logging.
- **Impact:** All material deduction now goes through DeductionService. tracking.py and tracking_api.py are thin callers.

### Phase 1b: Frontend Security Hardening
- **Files:** `kumar_frontend/register.html`, `kumar_frontend/js/main.js`, `kumar_frontend/js/config.js`, `kumar_frontend/js/modules/escapeHtml.js` (NEW)
- **Type:** fix
- **Details:** Removed dev token bypass (`?dev=1`), fixed XSS in showToast (innerHTML → textContent), JWT-based role extraction instead of trusting localStorage, canonical escapeHtml module.

### Phase 2: BOM (Bill of Materials) System
- **Files:** `backend_core/app/models_bom.py` (NEW), `backend_core/app/schemas_bom.py` (NEW), `backend_core/app/services/bom_service.py` (NEW), `backend_core/app/services/csv_template_service.py` (NEW), `backend_core/app/routers/bom.py` (NEW), `backend_core/app/security.py`, `backend_core/app/excel.py`, `backend_core/app/models.py`
- **Type:** feat
- **Details:** Full BOM system: Assembly → Parts → Material Requirements hierarchy. 18 new API endpoints at `/api/v2/bom/`. CSV/Excel import with assembly grouping. Template downloads for all import areas. BOM permissions added to all 6 roles. Backward compat bridge via nullable `assembly_id` FK on ProductionItem.

### Phase 3: Per-Piece Completion Tracking
- **Files:** `backend_core/app/services/stage_service.py` (NEW), `backend_core/app/routers/bom.py`
- **Type:** feat
- **Details:** StageService for piece-count tracking. Auto-completes stages when all pieces done. Progress dashboard endpoint. Added `completed_qty` to ProductionItem.

### Phase 4: Decompose Monolithic Files
- **Files:** `backend_core/app/services/scrap_service.py` (NEW), `backend_core/app/services/tracking_service.py` (NEW), `backend_core/app/services/excel_parser.py` (NEW), `backend_core/app/schemas_scrap.py` (NEW)
- **Type:** refactor
- **Details:** Extracted business logic from scrap.py (746 lines), tracking.py (857 lines), and excel.py into service layer. Original files remain as router shims for backward compatibility.

### Phase 5: Schema Anti-Pattern Fixes
- **Files:** `backend_core/app/models_v2.py`, `backend_core/app/models.py`
- **Type:** refactor
- **Details:** Added `UserRole` enum, `updated_at` to v1 tables, soft delete (`is_deleted`/`deleted_at`) to ProductionItem/Customer/Inventory, `ChecklistItem` normalized table, `active_only()` filter utility.

### Phase 6: Transaction Safety Hardening
- **Files:** `backend_core/app/models.py`
- **Type:** fix
- **Details:** Added `return_movement_id` to ScrapRecord for audit trail. DB-level `CheckConstraint('used <= total')` on Inventory. Fixed silent failures in tracking_api.py and tracking.py.

### Phase 7: Frontend Infrastructure
- **Files:** `kumar_frontend/js/modules/navbar.js` (NEW), `kumar_frontend/js/modules/store.js` (NEW), `kumar_frontend/js/modules/ui-components.js` (NEW), `kumar_frontend/js/modules/error-handler.js` (NEW), `kumar_frontend/js/modules/debounce.js` (NEW), `kumar_frontend/js/modules/pagination.js` (NEW)
- **Type:** feat
- **Details:** Dynamic navbar (replaces 23 hardcoded navbars), centralized state/cache/event bus, shared UI component factories, unified error handling, debounce utility, pagination component. All vanilla JS IIFE modules — no build step.

### Phase 8b: BOM Frontend Page
- **Files:** `kumar_frontend/bom.html` (NEW)
- **Type:** feat
- **Details:** BOM page with left panel assembly list (filterable by customer, lot), right panel detail view with parts table and per-piece completion status, progress bars, CSV import, template download.

### Test Suite: 16 passing, 2 skipped
- **Files:** `tests/unit/test_deduction_service.py`, `tests/concurrency/test_double_deduction.py`, `tests/regression/test_negative_inventory.py`
- **Type:** test
- **Details:** 11 unit tests (deduction happy path, idempotency, insufficient stock, auto-match, FIFO), 1 serial idempotency test, 4 regression tests (negative inventory prevention). 2 skipped (Postgres-only concurrency tests).

## [2026-03-28] Initial AI context system created
- **Files:** .ai/CONTEXT.md, .ai/PRIMER.md, .ai/CHANGELOG.md, .ai/DECISIONS.md, CLAUDE.md
- **Type:** docs
- **Details:** Created comprehensive AI context tracking system with architecture map, primer, change log, decision log, and project CLAUDE.md
- **Impact:** None (documentation only)
