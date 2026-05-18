# KBSteel ERP - Changelog

> Track what changed and why. Newest entries at top.

---

## 2026-05-18 — ERPNext Pattern Adaptation (6-Phase Architecture Upgrade)

### Added
- **Alembic migrations** — Proper schema management replacing hand-rolled `_run_migrations()`. Baseline migration for all 40+ tables. SQLite batch mode support.
- **Pytest infrastructure** — `conftest.py` with test DB, auth fixtures (5 roles), factory functions. 470 tests total, up from 14.
- **CI pipeline** — 4-job GitHub Actions: ruff lint, pytest + 60% coverage gate, mypy (advisory), Docker build.
- **Workflow engine** (`services/workflow_engine.py`) — Configurable state machine inspired by ERPNext Workflow doctype. Supports production stage flows (v1 + v3) and document status workflows (GRN/dispatch). Hook system for on_enter/on_exit actions.
- **Stock valuation** (`services/stock_valuation_service.py`) — FIFO and weighted-average valuation. 6 new columns on StockMovement. Wired into all movement creation points.
- **Accounting module** (`models_accounting.py`, `services/accounting_service.py`) — Double-entry ledger with chart of accounts, journal entries, trial balance. Auto-creates shadow entries from stock movements. Feature-flagged `ACCOUNTING_ENABLED=false`.
- **Print format engine** (`services/print_service.py`) — Jinja2 + xhtml2pdf. Templates for GRN, dispatch note, delivery challan. API: `GET /api/v2/print/{type}/{id}?format=html|pdf`.
- **Report builder** (`services/report_service.py`) — 8 predefined reports with Excel export. API: `GET /api/v2/reports/{name}`.
- **Enhanced dashboard** — 6 number cards (stock value, pending GRNs, production %, scrap rate, low stock alerts).
- **System settings** — Admin page + API for company profile, naming series, workflow config.
- **Enhanced naming series** — Configurable format tokens, Indian FY support, SQLite-safe.

### Refactored
- **scrap.py** (747→383 lines) → `ScrapService` + `ReusableStockService` + `ScrapAnalyticsService`
- **tracking.py** (761→477) + **tracking_api.py** (725→533) → `ExportService` + `TrackingService` expansion
- **Unified startup** — Single `create_all()` in dev, Alembic in prod.

### Fixed
- **split_item json import bug** — `json` used in `split_item()` but only imported locally inside another method. Silently caught by bare except. Moved to module-level.

### Feature Flags
- `USE_WORKFLOW_ENGINE=false` — Opt-in workflow engine for v1 stage tracking
- `ACCOUNTING_ENABLED=false` — Opt-in shadow accounting entries

---

## 2026-04-16 — Drawing-wise Tracking Integration + Codebase Cleanup

### Fixed
- **drawings.html navbar** — Fixed broken HTML structure: removed double-nested `d-none d-lg-flex` divs, added missing "Drawings" link, fixed closing tag structure. This was causing the page content to disappear when navigating to Drawings.
- **DrawingSummary schema** — Added missing `project_ref` field to `schemas_v3.py:DrawingSummary` and updated `_serialize_summary` in `drawings_v3.py` so the frontend table can display project references.
- **Duplicate class name** — Renamed first `DrawingMaterialSummary` to `DrawingWeightSummary` in `schemas_v3.py` to resolve silent class shadowing (Python's second class definition was overwriting the first).
- **XSS vulnerabilities** — Applied `escapeHtml()` to stage tags in drawing tracking cards and completed items table in `tracking_v2.html`.
- **Debug print** — Replaced `print()` with `logging.warning()` in `tracking_api.py` serialization error handler.
- **Stage mapping logic** — Fixed edge case where drawings with status COMPLETE but zero active instances would show in Fabrication column instead of Completed.

### Added
- **Drawing-wise tracking endpoint** — `GET /api/tracking/drawings` in `tracking_api.py` returns drawing-wise production tracking summaries with eager-loaded hierarchy, stage counts, overall stage placement, and completion percentage. Hard-limited to 200 results.
- **Drawings tab in Production Tracking** — Added "Drawings" tab to `tracking_v2.html` with:
  - Drawing-specific Kanban board (4 columns: Fabrication, Painting, Dispatch, Completed)
  - Drawing cards showing progress bars, stage distribution tags, weight, completion %
  - Customer and search filters
  - Stage stats pills
  - Clicking a drawing card navigates to the full Drawings page
- **N+1 query fix** — Added `selectinload` to `DrawingService.list_drawings()` for customer, assemblies, components, and instances.

### Removed (codebase cleanup)
- `kumar_frontend/tracking_DISABLED.html` — Explicitly disabled legacy page replaced by tracking_v2
- `backend_core/app/add_is_column.py` — One-time migration script no longer needed
- `.gcloud-tmp/` directory — Runtime OAuth artifacts that should never be in repo
- All `__pycache__/` and `.pytest_cache/` directories (project-level, excluding venv)
- Empty test subdirectories (`tests/concurrency/`, `tests/integration/`, `tests/regression/`, `tests/unit/`)
- Empty `tools/` directory

### Updated
- `.gitignore` — Added `.gcloud-tmp/` pattern

### Stats
- 172 total API routes (1 new: `/api/tracking/drawings`)
- Backend starts clean with all imports verified

---

## 2026-04-16 — v3 Phase 1 Implementation (Drawing-Based Production)

### Added
- `backend_core/app/models_v3.py` — 10 new tables: Drawing, Assembly, Component, ComponentInstance, StageTransition, MaterialReservation, StageConfig, DrawingRevision, RevisionChange + enums
- `backend_core/app/schemas_v3.py` — 27 Pydantic schemas for all v3 operations
- `backend_core/app/services/drawing_service.py` — Drawing CRUD, BOM management, weight calculations, release workflow
- `backend_core/app/services/component_tracking_service.py` — Per-component stage tracking, material deduction (v1+v2), kanban, batch operations
- `backend_core/app/routers/drawings_v3.py` — 18 new API endpoints at /api/v3/drawings/*
- `tests/test_v3_drawings.py` — 13 integration tests (all passing)
- Wired into main.py — v3 tables auto-created on startup, router registered

### Key Features
- Drawing → Assembly → Component → ComponentInstance hierarchy
- Independent stage tracking per component instance (cutting → drilling → fitting → welding → painting → qc → dispatch)
- Material reservation lifecycle: RESERVED → ISSUED → CONSUMED (with v2 StockMovement audit trail)
- Configurable stage pipeline per customer (StageConfig table with defaults)
- Immutable StageTransition audit log
- Drawing revision / ECN data model (ready for Phase 3)
- Kanban board API grouped by stage
- Batch stage advancement for bulk operations

### Stats
- 151 total API routes (18 new v3)
- 13 integration tests passing
- Backward compatible with v1 and v2

---

## 2026-04-16 — v3 Improvement Plan

### Added
- `.ai/PLAN_v3_improvements.md` — Master plan for v3 transformation (7 phases, 20 weeks)

### Why
- Client needs drawing-wise inventory deduction with individual component tracking
- Current system is flat (no hierarchy), needs Drawing → Assembly → Component model
- Plan covers: hierarchy, material reservation, revisions, cutting plans, reporting, QMS, CI/CD

---

## 2026-04-16 — Memory System & Codex Integration

### Added
- `.ai/PRIMER.md` — Quick orientation doc for agents/developers
- `.ai/CONTEXT.md` — Full architecture map (models, endpoints, services, frontend)
- `.ai/CHANGELOG.md` — This file
- `.ai/DECISIONS.md` — Architectural decision record
- `codex.md` — Project instructions for OpenAI Codex CLI
- `scripts/delegate-to-codex.sh` — Non-interactive Codex delegation script
- `.codex-output/` directory (gitignored) for Codex task outputs

### Why
- Enable fast context retrieval for AI agents (Claude Code + Codex)
- Create structured memory system referenced by CLAUDE.md
- Support multi-agent delegation workflows
