# KumarBrothers Steel ERP

Production-oriented ERP for a steel fabrication workflow. The system tracks customers, drawings, raw material receipts, inventory lots, production stages, dispatch, scrap, accounting records, reports, and role-based access.

[![CI](https://github.com/mangod12/industryERP/actions/workflows/ci.yml/badge.svg)](https://github.com/mangod12/industryERP/actions/workflows/ci.yml)
[![Deploy](https://github.com/mangod12/industryERP/actions/workflows/deploy.yml/badge.svg)](https://github.com/mangod12/industryERP/actions/workflows/deploy.yml)

## What Is In This Repo

| Area | Path | What it does |
|---|---|---|
| FastAPI app | `backend_core/app/main.py` | App factory, router mounting, CORS, startup DB setup, frontend file serving. |
| Domain models | `backend_core/app/models*.py` | v1, v2, v3, and accounting SQLAlchemy models. |
| Business services | `backend_core/app/services/` | Inventory, workflow, drawing, dispatch, reports, scrap, accounting, printing. |
| API routers | `backend_core/app/routers/` plus legacy modules | GRN, dispatch, drawings, inventory v2, reports, settings, print formats, and legacy routes. |
| Frontend | `kumar_frontend/` | Static HTML/CSS/JS pages served by FastAPI. |
| Migrations | `alembic/` | Alembic-managed production schema evolution. |
| Tests | `tests/` | Unit, integration, workflow, document, inventory, and E2E-style checks. |
| Deployment | `Dockerfile`, `deploy/`, `.github/workflows/` | Cloud Run build/deploy and container startup. |

## Business Flow

```text
Customer and drawing setup
  -> raw material receipt / GRN
  -> lot-level inventory and stock valuation
  -> drawing/component production stages
  -> fabrication, painting, QA, dispatch
  -> dispatch documents and reports
  -> scrap, reusable stock, accounting records
```

## Core Features

- Static frontend served by the FastAPI backend; no frontend build step.
- JWT authentication with role-based access.
- Customer, query, instruction, tracking, dashboard, notification, and user modules.
- v2 inventory operations for lot traceability, GRN, dispatch, and stock movement.
- v3 drawing-based production tracking.
- Auto material deduction through inventory/workflow services.
- Scrap and reusable stock management.
- Report and print-format generation using templates.
- Alembic migrations for production schema changes.
- Cloud Run deployment via GitHub Actions and Workload Identity Federation.

## Local Development

```bash
git clone https://github.com/mangod12/industryERP.git
cd industryERP

python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell users can use .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

uvicorn backend_core.app.main:app --reload --port 8000
```

Open:

- App: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Version: `http://localhost:8000/version`

In development mode, startup uses `create_all()` and seeds the local database. In production mode, use Alembic migrations.

## Configuration

Relevant environment variables include:

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `development` enables local schema creation; `production` expects Alembic-managed schema. |
| `DATABASE_URL` | Database URL. SQLite is used for local development when configured; PostgreSQL is used in production. |
| `KUMAR_SECRET_KEY` | JWT signing secret. |
| `CORS_ORIGINS` | Comma-separated allowed origins. |

Do not publish production credentials in this README. Use the configured seed/admin path or deployment secrets for real environments.

## API Organization

`backend_core/app/main.py` mounts these major groups:

- Legacy routes: `/auth`, `/users`, `/customers`, `/excel`, `/queries`, `/notifications`, `/instructions`, `/inventory`, `/dashboard`, `/scrap`, `/mappings`, `/tracking`.
- Tracking API: `/api/tracking`.
- v2/v3 routes: inventory v2, GRN, dispatch, drawings v3.
- Documents and reports: print formats and reports.
- Settings: company, naming series, notification, and system settings.

## Tests And Quality

CI runs:

```bash
ruff check backend_core/
ruff format --check backend_core/
python -m pytest tests/ -v --ignore=tests/test_every_page.py --ignore=tests/test_full_user_flows.py --cov=backend_core/app --cov-report=term-missing --cov-report=xml --cov-fail-under=60
docker build -t kbsteel-backend:test .
```

Local focused test run:

```bash
python -m pytest tests/ -v
```

## Deployment

The Cloud Run workflow:

1. Authenticates to Google Cloud through Workload Identity Federation.
2. Builds and pushes an image to Artifact Registry.
3. Deploys service `kbsteel-backend` in `asia-south1`.
4. Attaches Cloud SQL instance `kbsteel-pg`.
5. Verifies the live `/version` endpoint.

## Current Limitations

- The frontend is intentionally static HTML/JS; there is no frontend package manager or build pipeline.
- Production schema changes should go through Alembic, not startup `create_all()`.
- Some legacy v1 routes remain for compatibility while v2/v3 flows cover newer inventory and drawing workflows.

## License

MIT. See [LICENSE](LICENSE).
