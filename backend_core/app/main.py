import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before any module reads env vars

from fastapi import FastAPI
from .version import VERSION
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

# v3 Drawing-based production tracking
from .routers.drawings_v3 import router as drawings_v3_router


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
        version=VERSION,
        redirect_slashes=True
    )
    @app.get("/test-sanity")
    def test_sanity():
        return {"status": "ok"}

    @app.get("/version")
    def get_version():
        return {"version": VERSION, "app": "KBSteel ERP"}

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

    # v3 Drawing-based production tracking
    app.include_router(drawings_v3_router)

    # --- Serve Frontend Static Files ---
    # We use a custom static handler instead of app.mount("/", StaticFiles(...))
    # because StaticFiles at "/" intercepts all unmatched paths BEFORE FastAPI's
    # redirect_slashes middleware can normalize trailing slashes. This causes
    # /notifications (no slash) to 404 when the route is /notifications/ and
    # /customers/ (with slash) to 404 when the route is /customers.
    from pathlib import Path
    from fastapi.responses import FileResponse, HTMLResponse

    frontend_path = Path(__file__).resolve().parent.parent.parent / "kumar_frontend"

    if frontend_path.exists():
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            """Serve static frontend files. Only matches actual files on disk."""
            if not full_path:
                full_path = "index.html"

            file_path = frontend_path / full_path
            if file_path.is_file():
                # Determine content type
                suffix = file_path.suffix.lower()
                media_types = {
                    ".html": "text/html",
                    ".css": "text/css",
                    ".js": "application/javascript",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                    ".woff": "font/woff",
                    ".woff2": "font/woff2",
                    ".ttf": "font/ttf",
                }
                return FileResponse(
                    str(file_path),
                    media_type=media_types.get(suffix, "application/octet-stream")
                )

            # Try with .html extension (for clean URLs)
            html_path = frontend_path / f"{full_path}.html"
            if html_path.is_file():
                return FileResponse(str(html_path), media_type="text/html")

            return HTMLResponse(status_code=404, content="Not Found")
    
    @app.on_event("startup")
    def on_startup():
        print("[backend_core] Creating database tables at startup...")
        create_db_and_tables()
        # Also create v2 tables
        from .models_v2 import Base as BaseV2
        from .db import engine
        BaseV2.metadata.create_all(bind=engine)
        # v3 tables use same Base as v1 — already created by create_db_and_tables()
        from . import models_v3  # noqa: F401 — ensure v3 tables are registered
        from .db import Base as BaseV1
        BaseV1.metadata.create_all(bind=engine)
        print("[backend_core] Database ready (v1 + v2 + v3 tables).")

    return app


app = create_app()
