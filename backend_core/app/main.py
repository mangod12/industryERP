import os

from dotenv import load_dotenv

load_dotenv()  # Load .env before any module reads env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .customers import router as customers_router
from .dashboard import router as dashboard_router
from .db import create_db_and_tables
from .excel import router as excel_router
from .instructions import router as instructions_router
from .inventory import router as inventory_router
from .mappings import router as mappings_router
from .notifications import router as notifications_router
from .queries import router as queries_router
from .routers.dispatch import router as dispatch_router

# v3 Drawing-based production tracking
from .routers.drawings_v3 import router as drawings_v3_router
from .routers.grn import router as grn_router

# New v2 API routers for improved steel industry operations
from .routers.inventory_v2 import router as inventory_v2_router

# Print format document generation
from .routers.print_formats import router as print_formats_router

# Report builder
from .routers.reports import router as reports_router

# System settings (company, naming series, config)
from .routers.settings import router as settings_router
from .scrap import router as scrap_router
from .tracking import router as tracking_router
from .tracking_api import router as tracking_api_router
from .users import router as users_router
from .version import VERSION


def get_cors_origins():
    """Get CORS origins from environment or use defaults for development"""
    origins_env = os.getenv("CORS_ORIGINS", "")
    if origins_env:
        return [o.strip() for o in origins_env.split(",") if o.strip()]
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError("CORS_ORIGINS must be set explicitly in production")
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
        redirect_slashes=True,
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'",
        )
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.get("/test-sanity")
    def test_sanity():
        return {"status": "ok"}

    @app.get("/version")
    def get_version():
        return {"version": VERSION, "app": "KBSteel ERP"}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": VERSION}

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

    # Print format document generation
    app.include_router(print_formats_router)

    # v3 Drawing-based production tracking
    app.include_router(drawings_v3_router)

    # Report builder
    app.include_router(reports_router)

    # System settings
    app.include_router(settings_router)

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
                return FileResponse(str(file_path), media_type=media_types.get(suffix, "application/octet-stream"))

            # Try with .html extension (for clean URLs)
            html_path = frontend_path / f"{full_path}.html"
            if html_path.is_file():
                return FileResponse(str(html_path), media_type="text/html")

            return HTMLResponse(status_code=404, content="Not Found")

    @app.on_event("startup")
    def on_startup():
        env_mode = os.getenv("ENVIRONMENT", "development")

        if env_mode == "production":
            # In production, Alembic manages the schema.
            # Run: alembic upgrade head  (before deploying new code)
            print("[backend_core] Production mode — schema managed by Alembic.")
        else:
            # Development convenience: create_all() + seed admin user.
            # This keeps the "just run it" experience for local dev.
            print("[backend_core] Development mode — running create_all()...")
            create_db_and_tables()
            # Ensure v2 and v3 tables are also created
            from . import (
                models_accounting,  # noqa: F401 — register accounting tables
                models_v2,  # noqa: F401 — register v2 tables
                models_v3,  # noqa: F401 — register v3 tables
            )
            from .db import Base, engine

            Base.metadata.create_all(bind=engine)
            print("[backend_core] Database ready (v1 + v2 + v3 + accounting tables).")

    return app


app = create_app()
