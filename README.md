# KumarBrothers Steel ERP

[![CI](https://github.com/mangod12/industryERP/actions/workflows/ci.yml/badge.svg)](https://github.com/mangod12/industryERP/actions/workflows/ci.yml)
[![Deploy](https://github.com/mangod12/industryERP/actions/workflows/deploy.yml/badge.svg)](https://github.com/mangod12/industryERP/actions/workflows/deploy.yml)

Production-grade ERP for steel fabrication — tracks raw materials from receipt through fabrication, painting, dispatch, and scrap recovery.

---

## Live Demo

| | URL |
|---|---|
| **App** | [kbsteel-backend-498310931350.asia-south1.run.app](https://kbsteel-backend-498310931350.asia-south1.run.app) |
| **API Docs** | [/docs](https://kbsteel-backend-498310931350.asia-south1.run.app/docs) |
| **Version** | [/version](https://kbsteel-backend-498310931350.asia-south1.run.app/version) |

### Demo Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `AdminTest2026Kbs` | Boss (full access) |
| `supervisor` | *(contact admin)* | Software Supervisor |
| `storekeeper` | *(contact admin)* | Store Keeper |
| `qainspector` | *(contact admin)* | QA Inspector |
| `dispatchop` | *(contact admin)* | Dispatch Operator |
| `user` | *(contact admin)* | View-only |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.128.0, Python 3.12, Gunicorn + Uvicorn |
| ORM | SQLAlchemy 2.0.46, Pydantic v2 |
| Database | PostgreSQL (Cloud SQL) / SQLite (dev) |
| Frontend | Vanilla JS, Bootstrap 5.3.2, no build step |
| Auth | JWT (python-jose), bcrypt, 6 RBAC roles |
| Excel | pandas 3.0.0 + openpyxl for import/export |
| Deploy | Google Cloud Run, Artifact Registry, Cloud Build |
| CI/CD | GitHub Actions (Workload Identity Federation) |

---

## Core Business Flow

```
Raw Material Receipt (GRN) --> Weighbridge --> QA Inspection --> Stock Lot
     |
Customer Order --> Excel Upload (auto-link profiles to inventory)
     |
Fabrication --> Painting --> Dispatch --> Completed
     |                              |
Auto-deduct inventory          Dispatch note --> Weighbridge --> Ship
     |
Scrap/Waste --> Recovery or Write-off
```

## Key Features

- **Drawing-based production tracking (v3)** — Kanban board with per-component stage tracking
- **Dual inventory system** — v1 simple counts + v2 lot-level traceability with immutable audit trail
- **GRN/Dispatch workflows** — Goods receipt and dispatch with weighbridge integration
- **Auto material deduction** — Fabrication stage auto-deducts from inventory with double-deduction prevention
- **Excel import** — 90+ column alias matching, auto-links profiles to raw materials
- **6-role RBAC** — Boss, Supervisor, Store Keeper, QA Inspector, Dispatch Operator, User
- **Scrap management** — Track waste, recover reusable stock, loss analytics
- **Real-time dashboard** — Live counts, low stock alerts, auto-refresh

---

## Quick Start (Local Development)

```bash
# Clone and setup
git clone https://github.com/mangod12/industryERP.git
cd industryERP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start (SQLite dev DB created automatically)
uvicorn backend_core.app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) — frontend is served by FastAPI.

Admin credentials are printed to console on first startup.

---

## API Overview

**172 endpoints** across 3 API versions:

| Version | Prefix | Endpoints | Purpose |
|---|---|---|---|
| v1 | `/auth`, `/customers`, `/tracking`, etc. | 77 | Legacy CRUD, stage tracking |
| v2 | `/api/v2/*` | 27 | Lot-level inventory, GRN, dispatch |
| v3 | `/api/v3/*` | + | Drawing-based production tracking |

Full interactive docs at [`/docs`](https://kbsteel-backend-498310931350.asia-south1.run.app/docs).

---

## Project Structure

```
kbsteel-old/
├── backend_core/app/          # FastAPI application
│   ├── main.py                # App factory, router mounting
│   ├── models.py              # v1 models (15 tables)
│   ├── models_v2.py           # v2 models (12 tables)
│   ├── models_v3.py           # v3 drawing models (10 tables)
│   ├── security.py            # JWT, RBAC, rate limiting
│   ├── version.py             # Version tracking
│   ├── db.py                  # Engine, sessions, migrations
│   ├── services/              # Business logic layer
│   └── routers/               # v2/v3 API endpoints
├── kumar_frontend/            # 24 HTML pages, vanilla JS
│   ├── js/config.js           # Auth, API client, RBAC
│   └── css/main.css           # Theming
├── tests/                     # Test suite
│   ├── test_v3_drawings.py    # Unit tests (TestClient)
│   └── e2e_cloud_run.py       # 78 E2E tests against live deployment
├── .github/workflows/         # CI/CD pipelines
│   ├── ci.yml                 # Tests + Docker build verification
│   └── deploy.yml             # Cloud Build + Cloud Run deploy
├── Dockerfile                 # Production container
└── deploy/                    # nginx.conf, start.sh
```

---

## CI/CD Pipeline

```
git push main --> CI (tests + Docker build) --> Cloud Build --> Cloud Run (live)
```

- **CI:** Python 3.12 unit tests, Docker build verification on every push/PR
- **CD:** Automatic deploy to Cloud Run on push to `main` via Workload Identity Federation

---

## Deployment

### Google Cloud Run (Production)

The app auto-deploys to Cloud Run on push to `main`. Manual deploy:

```bash
gcloud run deploy kbsteel-backend \
  --source . \
  --region asia-south1 \
  --project kbsteel-erp \
  --allow-unauthenticated
```

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `KUMAR_SECRET_KEY` | prod | JWT signing key (min 32 chars) |
| `ENVIRONMENT` | no | `production` or `development` |
| `DATABASE_URL` | prod | PostgreSQL connection string |
| `CORS_ORIGINS` | no | Comma-separated allowed origins |

---

## License

Private — Kumar Brothers Steel Industry.
