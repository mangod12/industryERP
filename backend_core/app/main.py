import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before any module reads env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import create_db_and_tables  
from .auth import router as auth_router
from .customers import router as customers_router
from .tracking import router as tracking_router
from .queries import router as queries_router
from .instructions import router as instructions_router
from .inventory import router as inventory_router
from .excel import router as excel_router
from .notifications import router as notifications_router
from .users import router as users_router
from .dashboard import router as dashboard_router
from .tracking_api import router as tracking_api_router
from .scrap import router as scrap_router
from .mappings import router as mappings_router


# New v2 API routers for improved steel industry operations
from .routers.inventory_v2 import router as inventory_v2_router
from .routers.grn import router as grn_router
from .routers.dispatch import router as dispatch_router


def get_cors_origins():
    """Get CORS origins from environment or use defaults for development"""
    origins_env = os.getenv("CORS_ORIGINS", "")
    if origins_env:
        return [o.strip() for o in origins_env.split(",") if o.strip()]
    # Default development origins
    return [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://kumarbrothersbksc.in",
        "https://kumarbrothersbksc.in",
        "http://www.kumarbrothersbksc.in",
        "https://www.kumarbrothersbksc.in",
        "http://kumarbrothersbksc.in:5500",
        "http://kumarbrothersbksc.in:8081",
    ]


def create_app() -> FastAPI:
    app = FastAPI(
        title="KumarBrothers Steel Industry ERP",
        description="Inventory Management System for Steel Industry with full traceability",
        version="2.0.0"
    )
    @app.get("/test-sanity")
    def test_sanity():
        return {"status": "ok"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Legacy v1 routers (for backward compatibility)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(customers_router, prefix="/customers", tags=["customers"])
    app.include_router(excel_router, prefix="/excel", tags=["excel"])
    app.include_router(tracking_api_router, prefix="/api/tracking", tags=["tracking"])
    app.include_router(queries_router, prefix="/queries", tags=["queries"])
    app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
    app.include_router(instructions_router, prefix="/instructions", tags=["instructions"])
    app.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
    app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
    app.include_router(scrap_router, prefix="/scrap", tags=["scrap"])
    app.include_router(mappings_router, prefix="/mappings", tags=["mappings"])
    app.include_router(tracking_router, prefix="/tracking", tags=["tracking"])



    
    # New v2 routers (improved steel industry operations)
    app.include_router(inventory_v2_router)
    app.include_router(grn_router)
    app.include_router(dispatch_router)

    # --- Serve Frontend Static Files ---
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    
    frontend_path = Path(__file__).resolve().parent.parent.parent / "kumar_frontend"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    
    @app.on_event("startup")
    def on_startup():
        print("[backend_core] Creating database tables at startup...")
        create_db_and_tables()
        # Also create v2 tables
        from .models_v2 import Base as BaseV2
        from .db import engine
        BaseV2.metadata.create_all(bind=engine)
        print("[backend_core] Database ready (v1 + v2 tables).")

    return app


app = create_app()
