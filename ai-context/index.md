# IndustryERP AI Context

Last verified: 2026-06-15
Source repository: `https://github.com/mangod12/industryERP`
Source commit cloned: `a3c3bab5d0108272951f16ef67683ac13dd3d432`

## Purpose

This repository is KumarBrothers Steel ERP, a single-tenant steel fabrication and stock operations system. It combines a FastAPI backend with a static Bootstrap frontend served by the same FastAPI app.

Use this file as the first stop for future code work. The system has three generations of operations models:

- V1 legacy operations: customers, raw material inventory, production items, stage tracking, queries, instructions, notifications, scrap, reusable stock.
- V2 steel inventory: material master, stock lots, stock movements, GRN, dispatch notes, settings, reports, print formats, document workflow.
- V3 drawing production: drawings, assemblies, components, component instances, stage transitions, material reservations, revisions.

## Runtime Shape

Backend entrypoint: `backend_core.app.main:app`

Static frontend root: `kumar_frontend/`

Default local database: `backend_core/data/kbsteel_dev.db`

Production database: set `DATABASE_URL`. Production mode refuses to start without `DATABASE_URL`, `KUMAR_SECRET_KEY`, and explicit `CORS_ORIGINS`.

Important environment variables:

```powershell
$env:KUMAR_SECRET_KEY = "replace-with-strong-secret" # pragma: allowlist secret
$env:ENVIRONMENT = "development"
$env:DATABASE_URL = "sqlite:///H:/blue/industryERP/backend_core/data/kbsteel_dev.db"
$env:CORS_ORIGINS = "https://your-frontend.example"
```

## Local QA Workflow

Install Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Seed deterministic demo data:

```powershell
$env:KUMAR_SECRET_KEY = "dev-secret-key-minimum-32-characters" # pragma: allowlist secret
.\.venv\Scripts\python.exe scripts\seed_demo.py
```

Run the server:

```powershell
$env:KUMAR_SECRET_KEY = "dev-secret-key-minimum-32-characters" # pragma: allowlist secret
$env:ENVIRONMENT = "development"
.\.venv\Scripts\python.exe -m uvicorn backend_core.app.main:app --host 127.0.0.1 --port 8000
```

Demo login:

- Username: `admin`
- Password: `Boss1234!` <!-- pragma: allowlist secret -->

Run Python QA:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend_core tests scripts
.\.venv\Scripts\python.exe -m ruff format --check backend_core tests scripts
.\.venv\Scripts\pip-audit.exe -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\detect-secrets.exe scan --all-files --exclude-files "\.git|\.venv|node_modules|\.mypy_cache|\.pytest_cache|\.ruff_cache|dashboard\.png|Raw_materials\.png|customers_page\.png|production_tracking\.png|docs\\screenshots"
.\.venv\Scripts\python.exe -m pytest tests -q
cmd /c npm run test:syntax
```

Run browser QA:

```powershell
cmd /c npm install
cmd /c npx playwright install chromium
$env:E2E_BASE_URL = "http://127.0.0.1:8000"
$env:E2E_USERNAME = "admin"
$env:E2E_PASSWORD = "Boss1234!" # pragma: allowlist secret
cmd /c npm run test:e2e
```

Run design detection:

```powershell
cmd /c npm run design:impeccable
```

## Verified Status

Verified on 2026-06-15:

- `pip check`: passed.
- `pip-audit -r requirements.txt -r requirements-dev.txt`: no known vulnerabilities found.
- `ruff check backend_core tests scripts`: passed.
- `ruff format --check backend_core tests scripts`: passed after formatting touched files.
- `pytest tests -q`: 511 passed, 2 skipped.
- `npm run test:syntax`: passed for the Playwright spec and shared frontend JavaScript.
- `detect-secrets scan ...`: no findings after explicit false-positive allowlists.
- Playwright: 11 passed, major pages rendered, screenshots captured under `docs/screenshots/`, every authenticated HTML page plus login checked for shared shell visibility, page headings, accessible visible controls, invalid display values, page-level overflow, GRN/dispatch lifecycle state gates, typed raw-material reset confirmation, stock CSV export, customer permission filtering, password-toggle keyboard state, tablet viewport overflow, and the fabrication material-deduction modal gate.
- `npm run design:impeccable`: passed with zero reported anti-patterns after the factory UI hardening pass.
- `bandit -r backend_core/app -x tests`: 19 Low findings only. Most are broad `try/except/pass` and one false positive for token type `"bearer"`.
Known residuals:

- `mypy backend_core/app/services --ignore-missing-imports --no-strict-optional` still reports the existing SQLAlchemy typing baseline; CI already treats mypy as non-blocking.
- FastAPI/Pydantic deprecation warnings remain. They do not break tests today, but Pydantic V3 and FastAPI lifespan migration should be scheduled.
- The in-process rate limiter and token revocation model are not sufficient for multi-instance production without Redis or another shared store.

## Production-Hardening Changes Applied

- Runtime dependencies upgraded to remove known vulnerabilities: `fastapi==0.137.1`, `starlette==1.3.1`, `python-multipart==0.0.32`, `python-dotenv==1.2.2`, `pytest==9.1.0`.
- Deployment startup now runs `alembic upgrade head` before Gunicorn in Docker, Railway, Procfile, and deploy script.
- Dockerfile now copies `alembic/` and `alembic.ini`.
- Added `/healthz`; Railway healthcheck now uses it instead of `/docs`.
- Production CORS now requires explicit `CORS_ORIGINS`.
- Static frontend config now supports same-origin serving, `window.KB_API_BASE`, `localStorage.kb_api_base`, and `?apiBase=...`.
- Fixed dashboard link from missing `tracking.html` to `tracking_v2.html`.
- Live HTTP tests are gated by `RUN_LIVE_E2E=1`; no import-time network calls.
- Removed hardcoded production Playwright credentials from `tests/e2e_live_check.spec.js`.
- Protected `GET /notifications/roles/{role}` so users can only view their own role defaults unless they are Boss.
- Added deterministic `scripts/seed_demo.py` for local demo and Playwright data.
- Added `package.json`, `playwright.config.js`, and `tests/playwright/industry-erp.spec.js`.
- Added screenshot artifacts under `docs/screenshots/` for the manual.
- Global frontend polish: changed body font stack to Aptos/Segoe UI, added dropdown item padding, improved header action wrapping, improved tracking kanban desktop fit.
- All-page frontend polish: account settings and user registration now load the shared authenticated shell scripts, password visibility buttons have stable accessible names, and register/profile styling follows the shared steel-blue design tokens.
- Customer detail rendering no longer gets overwritten by the legacy shared customer-details handler, preventing visible `undefined` stage-history values.
- Added GRN and dispatch read-by-id endpoints used by the detail modals.
- Added `/api/v2/inventory/locations` so GRN approval can select an active yard/rack.
- Wired GRN filters, weighment recording, submit-for-QA, line QA approve/reject labels, approval location selection, and state-gated action buttons.
- Wired dispatch filters, detail view, manual lot picking, FIFO auto-pick, picked-line removal, submit-for-approval, confirm-dispatch, and state-gated action buttons.
- Added shared frontend `KBFormat` and `KBConfirm` helpers for operator-safe display values and high-stakes confirmations.
- Added Playwright coverage for visible button labels, Invalid Date/NaN leaks, and GRN/dispatch lifecycle controls.
- Cleared the full Impeccable static design audit by tightening the shared design system, replacing purple dispatch accents, improving contrast, flattening nested modal panels, fixing heading hierarchy, and increasing operator-friendly spacing.
- Expanded Playwright production smoke so it walks all authenticated HTML pages, discovers a seeded customer for edit/detail routes, verifies login before authentication, and fails on visible unnamed controls, `Invalid Date`, `NaN`, `undefined`, `null`, or page-level horizontal overflow.
- Fabrication completion now routes through the material-deduction preview modal before any stage-advance request is sent.
- Raw-material reset buttons now use typed `KBConfirm` confirmation, clearer labels, and toast-based failures instead of native dialogs.
- Stock overview now exports visible lots to CSV, loads movement history in the lot detail modal, and disables unsupported Hold/Release controls with a tooltip instead of presenting dead actions.
- User registration now uses the shared role catalog and backend permissions include Fabricator/Painter/legacy Dispatch roles for production operations.
- Fixed `/api/v2/inventory/movements/{lot_id}` to use `User.username` rather than a non-existent user display column.
- Number sequence generation now uses an atomic PostgreSQL `INSERT .. ON CONFLICT DO UPDATE RETURNING` path, with SQLite retaining the local-test path.
- GRN and dispatch approval hooks now refresh locked rows, reject inconsistent duplicate side effects, and behave idempotently after a document is already approved.
- CI now blocks on backend lint/format across `backend_core`, `tests`, and `scripts`; full pytest; pip-audit; JS syntax; Impeccable; and live Playwright browser QA before Docker build.

## Module Map

Backend:

- `backend_core/app/main.py`: app factory, router registration, static file serving, startup DB create for development.
- `backend_core/app/security.py`: JWT auth, role permissions, password hashing, security audit helpers.
- `backend_core/app/db.py`: SQLAlchemy engine/session and development table creation.
- `backend_core/app/models.py`: legacy users, customers, production items, inventory, notifications, scrap/reusable.
- `backend_core/app/models_v2.py`: steel inventory, GRN, dispatch, stock lots, movements, settings, audit.
- `backend_core/app/models_v3.py`: drawing, assembly, component, instance, reservation, revision.
- `backend_core/app/models_accounting.py`: accounts, fiscal years, journal entries, cost centers.
- `backend_core/app/routers/`: V2/V3 APIs for inventory, GRN, dispatch, reports, print formats, drawings, settings.
- `backend_core/app/services/`: inventory, workflow, report, print, production, tracking, drawing, accounting logic.

Frontend:

- `kumar_frontend/js/config.js`: API base and auth helpers.
- `kumar_frontend/js/main.js`: shared UI helpers, auth redirect, global fetch wrapper, notifications, legacy inventory/tracking wiring.
- `kumar_frontend/js/tracking_v2.js`: production tracking board behavior.
- `kumar_frontend/css/main.css`: shared design system.
- `kumar_frontend/*.html`: static pages for dashboard, inventory, GRN, dispatch, tracking, drawings, customers, scrap, reusable stock, queries, instructions, settings.

## Data Flow

1. User logs in through `/auth/login`; token and role are stored in browser local storage.
2. Static pages call APIs through `KBConfig.API_BASE`, defaulting to same origin.
3. Inventory V1 tracks simple material totals and consumption.
4. Inventory V2 tracks material masters, stock lots, immutable stock movements, GRN inward flow, dispatch outward flow, and stock reports.
5. Production V1/V2 tracks customers and production items through fabrication, painting, and dispatch.
6. Production V3 tracks shop drawings down to component instances and reserves/issues/consumes material against those instances.
7. Scrap and reusable stock record losses, recoverable material, and dashboard loss analytics.
