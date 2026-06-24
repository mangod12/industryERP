# IndustryERP Deep Recon - 2026-06-24

## Scope

This recon maps the current `industryERP` checkout after the upload-template and auto-refresh fixes made on 2026-06-24. It is intended as a durable context structure for future implementation, review, and client-facing triage.

Primary evidence used:

- `README.md`, `PRODUCT.md`, `DESIGN.md`, `docs/ARCHITECTURE_REVIEW.md`
- `backend_core/app/main.py`, `db.py`, `deps.py`, `security.py`
- Backend route declarations in `backend_core/app/**/*.py`
- Frontend pages under `kumar_frontend/`
- Tests under `tests/` and `tests/playwright/industry-erp.spec.js`
- CI/deploy config in `.github/workflows/`, `Dockerfile`, `Procfile`, `railway.json`, `deploy/start.sh`

## Product Shape

KumarBrothers Steel ERP is a single-tenant plant operations system for steel fabrication. The core users are management, store keepers, QA inspectors, dispatch operators, and production supervisors. The UX should stay dense, clear, bright, and operator-safe rather than decorative.

The repo has three application generations living together:

1. Legacy operations: customers, production items, stage tracking, raw inventory, queries, instructions, notifications, scrap, reusable stock.
2. V2 steel inventory: material master, stock lots, stock movements, GRN, dispatch, reports, print formats, settings, document workflow.
3. V3 drawing production: drawings, assemblies, components, component instances, stage transitions, material reservations, revisions.

## Runtime Map

- Backend: FastAPI app exported as `backend_core.app.main:app`.
- Frontend: static HTML/CSS/JS in `kumar_frontend/`, served by FastAPI through the catch-all static file handler.
- Local database: SQLite at `backend_core/data/kbsteel_dev.db` when `DATABASE_URL` is absent.
- Production database: `DATABASE_URL` is mandatory when `ENVIRONMENT=production`.
- Auth: JWT bearer token stored by the static frontend, generated through `/auth/login`.
- Migrations: Alembic is used in production startup; development still uses `create_all()` for convenience.

Local run shape:

```powershell
$env:KUMAR_SECRET_KEY = "dev-secret-key-minimum-32-characters"
$env:ENVIRONMENT = "development"
.\.venv\Scripts\python.exe -m uvicorn backend_core.app.main:app --host 127.0.0.1 --port 8000
```

## Backend Context

Core files:

- `backend_core/app/main.py`: app construction, middleware, router inclusion, health/version endpoints, static frontend serving, development startup table creation.
- `backend_core/app/db.py`: SQLAlchemy engine/session, local SQLite fallback, legacy hand-written PostgreSQL migration shim, default admin seeding.
- `backend_core/app/security.py`: JWT, password policy, role permissions, permission dependencies, audit logging helpers, in-memory rate limiter.
- `backend_core/app/deps.py`: separate dependency layer used by legacy routes; duplicates some auth/RBAC concepts from `security.py`.
- `backend_core/app/models.py`: legacy user/customer/production/inventory/scrap/reusable models.
- `backend_core/app/models_v2.py`: material master, stock lots, stock movements, GRN, dispatch, audit, settings, number sequences.
- `backend_core/app/models_v3.py`: drawing, assembly, component, component instance, material reservation, transitions, revisions.
- `backend_core/app/models_accounting.py`: accounting module models.

Router groups:

- Legacy: `auth.py`, `users.py`, `customers.py`, `excel.py`, `tracking.py`, `tracking_api.py`, `inventory.py`, `dashboard.py`, `scrap.py`, `queries.py`, `instructions.py`, `notifications.py`, `mappings.py`.
- V2: `routers/inventory_v2.py`, `routers/grn.py`, `routers/dispatch.py`, `routers/reports.py`, `routers/settings.py`, `routers/print_formats.py`.
- V3: `routers/drawings_v3.py`.

Service layer:

- Stock/document/business rules live mainly in `services/inventory_service.py`, `workflow_engine.py`, `production_service.py`, `tracking_service.py`, `scrap_service.py`, `component_tracking_service.py`, `drawing_service.py`, `inventory_bridge.py`, `report_service.py`, `print_service.py`, `accounting_service.py`.

Backend observation:

- The project has a real service layer and meaningful tests, but several service/router files are large enough that changes require careful blast-radius checks.
- Legacy routes use `deps.py` role checks while v2 routes use permission checks from `security.py`. This split is functional but makes authorization drift likely.
- Development schema creation and production Alembic migration are intentionally different. This improves local startup but creates a schema-drift risk unless migrations and model changes are kept synchronized.

## Frontend Context

Shared assets:

- `kumar_frontend/js/config.js`: API base resolution, token helpers, role-aware UI helpers.
- `kumar_frontend/js/main.js`: shared shell, toast, `KBConfirm`, `KBFormat`, global fetch wrapper, notifications, legacy page handlers.
- `kumar_frontend/css/main.css`: design system and shared layout.
- `kumar_frontend/partials/sidebar.html`: authenticated navigation.
- `kumar_frontend/templates/*.csv`: operator-facing import templates.

Important pages:

- `index.html`: dashboard and polling metrics.
- `customers.html`: customers, production upload preview/import, template guidance.
- `tracking_v2.html`: production tracking board and reports.
- `drawings.html`: V3 drawing and component tracking UI.
- `raw_material.html`, `materials.html`, `stock.html`, `grn.html`, `dispatch.html`: inventory and document workflows.
- `scrap.html`, `reusable.html`: scrap and reusable material lifecycle.
- `settings.html`, `system-settings.html`, `notification-settings.html`, `account-settings.html`, `register.html`: admin and account surfaces.

Frontend hotspots by line count:

- `tracking_v2.html`: 1428 lines.
- `kumar_frontend/js/main.js`: 1247 lines.
- `dispatch.html`: 1100 lines.
- `drawings.html`: 892 lines.
- `grn.html`: 868 lines.
- `scrap.html`: 760 lines.
- `customers.html`: 703 lines.

Frontend observation:

- The current static approach is lightweight and deploys simply, but page-level inline scripts are now beyond the size where changes remain easy to reason about.
- The prior disruptive auto-refresh behavior was addressed in `drawings.html`, `scrap.html`, and `reusable.html`. Remaining refresh-like behavior is mostly dashboard/notification polling and global fetch UI side effects.
- Native `alert`, `confirm`, and `prompt` still exist in several pages. High-stakes operator workflows should consistently use `KBConfirm` and toast/modal error states.

## Upload and Template Context

Template assets currently on disk:

- `production_tracking_tcil_template.csv`
- `assembly_list_template.csv`
- `assembly_part_list_template.csv`
- `stage_update_template.csv`
- `scrap_import_template.csv`
- `IMPORT_GUIDE.md`

Implemented 2026-06-24:

- `GET /excel/templates` returns template metadata and download URLs.
- `customers.html` shows production tracking template guidance before upload and compares detected columns to expected template columns during preview.
- `scrap.html` shows scrap template guidance and previews uploads before writing records.
- `POST /scrap/preview-upload` previews grouped scrap data without import side effects.
- Backend tests cover template listing and scrap preview behavior.

Remaining template gaps:

- Stage update, assembly list, and assembly part templates are present on disk but not fully surfaced as first-class upload flows in the UI.
- Template metadata currently lives in `backend_core/app/excel.py`; parser aliases and import behavior live in service/parser code. That can drift unless the metadata is generated from shared import specifications.
- The UI explains required/recommended columns, but there is no persistent upload history, rejected-row download, or rollback workflow yet.

## Refresh and Client Complaint Context

Resolved:

- Full-page auto-refresh was removed from the affected scrap/reusable/drawing workflows.
- Playwright now checks for disruptive short `setInterval` behavior on pages where users inspect records.
- The global fetch wrapper now supports `interactive`, `background`, and `silent` request modes through `window.KBRequest` and custom fetch options.
- Dashboard and shared notification polling are marked as background requests, so they do not show the global loader or generic success/error toasts during routine refreshes.

Still relevant:

- `index.html` polls dashboard data every 30 seconds and notifications every 60 seconds.
- `kumar_frontend/js/main.js` polls notifications every 30 seconds for authenticated shell pages.
- The global fetch wrapper displays loader/toast behavior for many requests. Even without page reloads, this can feel like the page is constantly refreshing.
- Some actions still call broad reload/load functions after mutation. This is acceptable for small lists but feels disruptive when users are reading detail panels or upload previews.

Recommended direction:

- Keep dashboard polling, but stop global loader/toast behavior for background polling.
- Introduce explicit request intent: `interactive`, `background`, `silent`, `mutation`.
- Preserve scroll position, active tabs, selected filters, open modals, and selected records after data refresh.
- Replace whole-list reloads with local row/state updates where practical.

## QA and CI Context

Available verification:

- Python lint/format through Ruff.
- Pytest suite with service, API, workflow, document, accounting, reporting, upload-template, and smoke coverage.
- Playwright browser QA under `tests/playwright/industry-erp.spec.js`.
- JS syntax check for shared JS and Playwright spec.
- Impeccable design audit.
- Pip audit in CI.
- Docker build/start verification in CI.

Recent verified commands from the 2026-06-24 implementation pass:

- `pytest tests\test_upload_templates.py`
- `pytest tests\test_upload_templates.py tests\test_production_service.py`
- `ruff check backend_core\app\excel.py backend_core\app\scrap.py backend_core\app\services\scrap_service.py tests\test_upload_templates.py`
- `npm run test:syntax`
- `npm run test:e2e`
- `git diff --check`
- `pytest tests\test_upload_templates.py tests\test_smoke.py -q`
- `npx playwright test -g "background dashboard refreshes"`

Residual QA gaps:

- The Playwright suite is strong as smoke/regression coverage, but it does not yet exercise every import template end-to-end.
- Authorization matrix tests are uneven across legacy, v2, and v3 routers.
- Global fetch side effects need targeted browser tests so background polling cannot reintroduce visible UI churn.
- Upload workflows need rejected-row and malformed-file tests.

## Risk Register

### High: Frontend scripts are too large and too global

Evidence:

- `tracking_v2.html`, `main.js`, `dispatch.html`, `drawings.html`, and `grn.html` are the largest files in the repo.
- Shared `main.js` owns shell behavior, global fetch behavior, notifications, formatting, confirmations, and legacy page handlers.

Impact:

- Small fixes can affect unrelated pages.
- Refresh/toast/loading behavior is hard to reason about because it is global.
- Client complaints about pages "refreshing too much" can return as new workflows are added.

Action:

- Split page-specific logic into `kumar_frontend/js/pages/*.js`.
- Keep `main.js` limited to shell, auth, shared UI primitives, and explicit API helpers.
- Add browser tests for "background refresh does not close modals, reset forms, or move scroll."

### High: Authorization is split across two dependency systems

Evidence:

- Legacy routers mostly import from `backend_core/app/deps.py`.
- V2 routers import `require_permission` and `get_db` from `backend_core/app/security.py`.

Impact:

- Roles and permissions can diverge.
- An authenticated user may get different access behavior depending on API generation.
- Security review has to inspect two abstractions instead of one.

Action:

- Make `security.py` the single source of auth/RBAC truth.
- Keep `deps.py` only as compatibility wrappers or remove it after route migration.
- Add a role-by-endpoint authorization matrix test.

### High: Import/template metadata can drift from actual parser behavior

Evidence:

- UI template guidance is backed by `UPLOAD_TEMPLATES` in `excel.py`.
- Actual normalization and import behavior lives in import endpoints and services.

Impact:

- Client may download a template that the parser only partially accepts.
- Guidance can say a column is required while the import code accepts or rejects a different shape.

Action:

- Define import specs as structured objects with `template columns`, `aliases`, `required fields`, `preview`, and `commit` behavior.
- Generate API metadata and CSV templates from those specs.
- Add contract tests that each template can preview and import at least one valid row.

### Medium: Migration strategy is two-track

Evidence:

- Production startup runs Alembic.
- Development startup still uses `Base.metadata.create_all()`.
- `db.py` retains an older hand-written PostgreSQL migration shim marked deprecated.

Impact:

- Local tests may pass with tables created directly while production needs an Alembic migration.
- Deprecated migration code adds cognitive noise and another path to audit.

Action:

- Keep dev convenience, but add CI check that Alembic head can create a fresh database.
- Remove the hand-written migration shim after production Alembic is trusted.
- Require every schema/model change to include an Alembic migration or an explicit no-migration note.

### Medium: Operator actions still use browser-native dialogs

Evidence:

- Static scan found native `alert`, `confirm`, and `prompt` in customer details, dispatch, drawings, instructions, reusable, scrap, queries, and shared JS.

Impact:

- Native dialogs are inconsistent, hard to style, and easy to mis-click.
- They do not preserve enough context for destructive or high-stakes plant operations.

Action:

- Replace native dialogs with `KBConfirm` and structured Bootstrap modals.
- Use typed confirmation for destructive actions and clear summaries for bulk operations.

### Medium: Observability and recovery are thin around critical data changes

Evidence:

- There are audit helpers and movement logs, but legacy routes still contain broad exception swallowing and TODO notes around audit logging.

Impact:

- When stock, stage, import, or delete workflows fail partially, operators may not know what changed.
- Support cannot reconstruct all client complaints from audit trails.

Action:

- Add audit events for imports, upload previews, stage changes, destructive deletes, scrap status changes, and reusable returns.
- Add correlation IDs for API requests and include them in UI error messages.
- Add upload job history with status, row counts, warnings, and downloadable rejection files.

### Medium: Static API route declaration should be monitored after FastAPI upgrade

Evidence:

- Runtime route introspection on FastAPI 0.137 reported included routers as wrapper objects rather than ordinary flattened `APIRoute` entries, while source router declarations and tests still cover the API surface.

Impact:

- Custom tooling that expects `app.routes` to be fully flattened may miss included API routes.
- This is a tooling/documentation risk unless runtime requests fail.

Action:

- Keep API smoke tests as the source of truth.
- If route inventory tooling is needed, use source declaration scanning or FastAPI's OpenAPI schema rather than raw `app.routes`.

## What Else Can Be Done

Priority 1:

- Build a frontend request-state contract so background polling does not show global loaders or success toasts.
- Split `main.js` into shell/auth/API/notification modules plus page-specific files.
- Add modal/scroll/form preservation tests for dashboard, drawings, scrap, reusable, customers upload, GRN, and dispatch.

Priority 2:

- Convert all upload templates into import specs and generate both the metadata endpoint and CSV template files from the same source.
- Surface all available templates in a dedicated "Import Center" or upload assistant view.
- Add upload history, rejected-row downloads, and dry-run/commit separation for every import path.

Priority 3:

- Consolidate auth dependencies and add endpoint authorization matrix tests.
- Add import/stage/delete audit logs with correlation IDs.
- Tighten Alembic discipline and remove the deprecated hand-written migration shim.

Priority 4:

- Replace remaining native dialogs with `KBConfirm` or workflow-specific modals.
- Reduce page file sizes below the project standard by moving inline scripts out of HTML.
- Add performance checks for N+1 detail fetches in kanban/dashboard-style views.

## Devil's Advocate Review

Here is what the current approach gets right: the application favors a simple deployment model, has meaningful backend services, uses real browser smoke tests, and now gives users safer upload previews for production tracking and scrap. For a plant-floor ERP, keeping the frontend static and backend monolithic is a reasonable choice while the product is still consolidating workflows.

Concern: The frontend architecture will keep recreating the refresh complaint.
Severity: High
Framework: Pre-mortem

What I see:
Global fetch behavior, repeated polling, and page-level reload/load functions are spread across large inline scripts and `main.js`.

Why it matters:
Even after removing full-page auto-refresh, users can still experience unexpected spinners, toasts, modal resets, filter resets, and list jumps.

What to do:
Define request intent and page state preservation as first-class frontend contracts, then test them with Playwright.

Concern: Template guidance can become confidently wrong.
Severity: High
Framework: AI blind spot - confidence without correctness

What I see:
Template metadata, CSV files, parser aliases, and service normalization are not generated from a single import spec.

Why it matters:
The UI can tell the client to upload one shape while the backend actually accepts another. That damages trust faster than a missing feature.

What to do:
Move upload formats into shared import specs and test every downloadable template against preview and commit paths.

Concern: Authorization review is harder than it needs to be.
Severity: High
Framework: Red team / blue team

What I see:
Legacy routes and v2 routes use different dependency modules and role/permission styles.

Why it matters:
Authenticated-but-unauthorized access bugs hide in exactly this kind of split.

What to do:
Unify auth dependencies and enforce a role-by-endpoint matrix test in CI.

Concern: The codebase has grown beyond "static pages with scripts" ergonomics.
Severity: Medium
Framework: Inversion

What I see:
Several HTML files exceed 800 lines, and shared JS exceeds 1200 lines.

Why it matters:
The easiest way to make future work fail is to keep adding behavior into those files. The next maintainer will miss an interaction.

What to do:
Extract page modules and shared API helpers incrementally, starting with upload, scrap/reusable, and dashboard polling code.

Concern: Critical data mutations need better recovery and audit UX.
Severity: Medium
Framework: Data lifecycle blind spot

What I see:
Movement/audit infrastructure exists, but legacy workflows still have broad exception swallowing and incomplete audit coverage.

Why it matters:
When stock or production data looks wrong, the client needs a trail, not a guess.

What to do:
Add audit events and upload job history for imports, stage changes, destructive deletes, scrap actions, and reusable returns.

Verdict: Ship with changes. The recent fixes are directionally right, but the next high-value work should be architecture guardrails around frontend request state, generated import specs, and unified authorization. Adding more workflows before those guardrails will multiply the same client complaints.
