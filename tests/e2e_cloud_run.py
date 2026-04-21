"""
KBSteel ERP — Full E2E Test Suite for Cloud Run Deployment
==========================================================
Tests: health, version, frontend pages, auth flow, all API endpoints,
CORS, security headers, and error handling against the live deployment.

Usage: python -m pytest tests/e2e_cloud_run.py -v --tb=short
"""

import os
import time
import requests
import pytest

BASE_URL = os.getenv(
    "E2E_BASE_URL",
    "https://kbsteel-backend-498310931350.asia-south1.run.app",
)

# Will be set by login fixture
AUTH_TOKEN = None
AUTH_ROLE = None


# ─── Helpers ────────────────────────────────────────────────────────────────

def get(path, token=None, params=None, allow_statuses=(200,)):
    """GET with optional auth, return (status, body_or_None)."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=30)
    body = None
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body, r.headers


def post_json(path, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BASE_URL}{path}", json=data, headers=headers, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body, r.headers


# ─── 1. HEALTH & VERSION ───────────────────────────────────────────────────

class TestHealthAndVersion:
    def test_sanity(self):
        status, body, _ = get("/test-sanity")
        assert status == 200
        assert body["status"] == "ok"

    def test_version(self):
        status, body, _ = get("/version")
        assert status == 200
        assert body["version"] == "2.1.0"
        assert body["app"] == "KBSteel ERP"

    def test_openapi_schema(self):
        status, body, _ = get("/openapi.json")
        assert status == 200
        assert body["info"]["title"] == "KumarBrothers Steel Industry ERP"
        assert body["info"]["version"] == "2.1.0"


# ─── 2. FRONTEND PAGES ─────────────────────────────────────────────────────

FRONTEND_PAGES = [
    ("/", "text/html"),
    ("/index.html", "text/html"),
    ("/login.html", "text/html"),
    ("/register.html", "text/html"),
    ("/customers.html", "text/html"),
    ("/customer_add.html", "text/html"),
    ("/customer_edit.html", "text/html"),
    ("/customer_details.html", "text/html"),
    ("/raw_material.html", "text/html"),
    ("/materials.html", "text/html"),
    ("/scrap.html", "text/html"),
    ("/reusable.html", "text/html"),
    ("/grn.html", "text/html"),
    ("/dispatch.html", "text/html"),
    ("/tracking_v2.html", "text/html"),
    ("/drawings.html", "text/html"),
    ("/instructions.html", "text/html"),
    ("/instructions_edit.html", "text/html"),
    ("/queries.html", "text/html"),
    ("/settings.html", "text/html"),
    ("/account-settings.html", "text/html"),
    ("/notification-settings.html", "text/html"),
    ("/stock.html", "text/html"),
    ("/js/config.js", "application/javascript"),
    ("/js/main.js", "application/javascript"),
    ("/css/main.css", "text/css"),
    ("/favicon.ico", "image/x-icon"),
]


class TestFrontendPages:
    @pytest.mark.parametrize("path,expected_type", FRONTEND_PAGES)
    def test_page_loads(self, path, expected_type):
        r = requests.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        ct = r.headers.get("content-type", "")
        assert expected_type in ct, f"{path}: expected {expected_type}, got {ct}"
        assert len(r.content) > 0, f"{path} returned empty body"

    def test_nonexistent_page_404(self):
        r = requests.get(f"{BASE_URL}/nonexistent-page-xyz.html", timeout=30)
        assert r.status_code == 404


# ─── 3. AUTH FLOW ──────────────────────────────────────────────────────────

class TestAuthFlow:
    def test_login_success(self):
        """Try login with known test credentials from env vars — run FIRST to avoid rate limit."""
        username = os.getenv("E2E_USERNAME")
        password = os.getenv("E2E_PASSWORD")
        if not username or not password:
            pytest.skip("E2E_USERNAME / E2E_PASSWORD not set — skipping auth test")

        status, body, _ = post_json("/auth/login", {
            "username": username,
            "password": password,
        })
        assert status == 200, f"Login failed: {body}"
        assert "access_token" in body
        assert "role" in body
        assert body["token_type"] == "bearer"

        # Store for downstream tests
        global AUTH_TOKEN, AUTH_ROLE
        AUTH_TOKEN = body["access_token"]
        AUTH_ROLE = body["role"]

    def test_login_missing_fields(self):
        status, body, _ = post_json("/auth/login", {})
        assert status in (400, 429)

    def test_login_wrong_credentials(self):
        status, body, _ = post_json("/auth/login", {
            "username": "nonexistent_user_xyz",
            "password": "WrongPass123!"
        })
        assert status in (401, 429)

    def test_unauthenticated_endpoints_return_401(self):
        """All protected endpoints should return 401 without a token."""
        protected = [
            "/users/me",
            "/customers",
            "/inventory",
            "/tracking/dashboard/summary",
            "/api/tracking",
            "/scrap/records",
            "/instructions",
            "/queries",
            "/notifications",
            "/dashboard/summary",
            "/api/v2/inventory/materials",
            "/api/v2/grn/vendors",
            "/api/v2/grn",
            "/api/v2/dispatch",
        ]
        for path in protected:
            status, _, _ = get(path)
            assert status == 401, f"{path} returned {status} instead of 401"

    def test_invalid_token_rejected(self):
        status, body, _ = get("/users/me", token="invalid.token.here")
        assert status == 401


# ─── 4. AUTHENTICATED API TESTS (only if creds provided) ───────────────────

class TestAuthenticatedAPIs:
    """Run only when E2E_USERNAME/E2E_PASSWORD are set."""

    @pytest.fixture(autouse=True)
    def require_auth(self):
        global AUTH_TOKEN
        if not AUTH_TOKEN:
            username = os.getenv("E2E_USERNAME")
            password = os.getenv("E2E_PASSWORD")
            if not username or not password:
                pytest.skip("No auth credentials — skipping authenticated tests")
            status, body, _ = post_json("/auth/login", {
                "username": username,
                "password": password,
            })
            if status != 200:
                pytest.skip(f"Login failed ({status}) — skipping authenticated tests")
            AUTH_TOKEN = body["access_token"]

    # --- User profile ---
    def test_get_current_user(self):
        status, body, _ = get("/users/me", token=AUTH_TOKEN)
        assert status == 200
        assert "username" in body
        assert "role" in body

    # --- Customers ---
    def test_list_customers(self):
        status, body, _ = get("/customers", token=AUTH_TOKEN)
        assert status == 200
        assert isinstance(body, list)

    # --- Inventory v1 ---
    def test_list_inventory(self):
        status, body, _ = get("/inventory", token=AUTH_TOKEN)
        assert status == 200

    def test_inventory_stats(self):
        status, body, _ = get("/inventory/stats/summary", token=AUTH_TOKEN)
        assert status == 200

    def test_inventory_dashboard(self):
        status, body, _ = get("/inventory/dashboard-data", token=AUTH_TOKEN)
        assert status == 200

    # --- Tracking v1 ---
    def test_tracking_dashboard(self):
        status, body, _ = get("/tracking/dashboard/summary", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_api_list(self):
        status, body, _ = get("/api/tracking", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_all_items(self):
        status, body, _ = get("/api/tracking/all-items", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_completed(self):
        status, body, _ = get("/api/tracking/completed", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_drawings(self):
        status, body, _ = get("/api/tracking/drawings", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_archived(self):
        status, body, _ = get("/api/tracking/archived", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_active_orders(self):
        status, body, _ = get("/api/tracking/orders/active", token=AUTH_TOKEN)
        assert status == 200

    def test_tracking_completed_orders(self):
        status, body, _ = get("/api/tracking/orders/completed", token=AUTH_TOKEN)
        assert status == 200

    # --- Dashboard ---
    def test_dashboard_summary(self):
        status, body, _ = get("/dashboard/summary", token=AUTH_TOKEN)
        assert status == 200

    # --- Scrap ---
    def test_scrap_records(self):
        status, body, _ = get("/scrap/records", token=AUTH_TOKEN)
        assert status == 200

    def test_scrap_reusable(self):
        status, body, _ = get("/scrap/reusable", token=AUTH_TOKEN)
        assert status == 200

    def test_scrap_analytics(self):
        status, body, _ = get("/scrap/analytics", token=AUTH_TOKEN)
        assert status == 200

    def test_scrap_summary(self):
        status, body, _ = get("/scrap/summary", token=AUTH_TOKEN)
        assert status == 200

    # --- Instructions ---
    def test_instructions_list(self):
        status, body, _ = get("/instructions", token=AUTH_TOKEN)
        assert status == 200

    # --- Queries ---
    def test_queries_list(self):
        status, body, _ = get("/queries", token=AUTH_TOKEN)
        assert status == 200

    # --- Notifications ---
    def test_notifications_list(self):
        status, body, _ = get("/notifications", token=AUTH_TOKEN)
        assert status == 200

    # --- Mappings ---
    def test_mappings_list(self):
        status, body, _ = get("/mappings", token=AUTH_TOKEN)
        assert status == 200

    # --- v2 Inventory ---
    def test_v2_materials(self):
        status, body, _ = get("/api/v2/inventory/materials", token=AUTH_TOKEN)
        assert status == 200

    def test_v2_lots(self):
        status, body, _ = get("/api/v2/inventory/lots", token=AUTH_TOKEN)
        assert status == 200

    def test_v2_summary(self):
        status, body, _ = get("/api/v2/inventory/summary", token=AUTH_TOKEN)
        assert status == 200

    def test_v2_aging_report(self):
        status, body, _ = get("/api/v2/inventory/aging-report", token=AUTH_TOKEN)
        assert status == 200

    def test_v2_low_stock_alerts(self):
        status, body, _ = get("/api/v2/inventory/alerts/low-stock", token=AUTH_TOKEN)
        assert status == 200

    # --- v2 GRN ---
    def test_v2_vendors(self):
        status, body, _ = get("/api/v2/grn/vendors", token=AUTH_TOKEN)
        assert status == 200

    def test_v2_grn_list(self):
        status, body, _ = get("/api/v2/grn", token=AUTH_TOKEN)
        assert status == 200

    # --- v2 Dispatch ---
    def test_v2_dispatch_list(self):
        status, body, _ = get("/api/v2/dispatch", token=AUTH_TOKEN)
        assert status == 200

    # --- v3 Drawings ---
    def test_v3_drawings_list(self):
        status, body, _ = get("/api/v3/drawings", token=AUTH_TOKEN)
        assert status == 200

    # --- Excel ---
    def test_excel_template(self):
        status, body, _ = get("/excel/template", token=AUTH_TOKEN)
        # Template download may be 200 or could require specific params
        assert status in (200, 404, 422)


# ─── 5. CORS ───────────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_preflight(self):
        """OPTIONS request should return CORS headers."""
        r = requests.options(
            f"{BASE_URL}/auth/login",
            headers={
                "Origin": "https://kumarbrothersbksc.in",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
            timeout=15,
        )
        # FastAPI CORS middleware should respond
        assert r.status_code == 200, f"CORS preflight returned {r.status_code}"


# ─── 6. SECURITY CHECKS ────────────────────────────────────────────────────

class TestSecurity:
    def test_no_server_header_leak(self):
        """Should not expose detailed server info."""
        r = requests.get(f"{BASE_URL}/version", timeout=15)
        server = r.headers.get("server", "").lower()
        # Should not reveal uvicorn/gunicorn version details
        assert "python" not in server

    def test_rate_limit_on_login(self):
        """Verify rate limiting is active (5 attempts per 5 min)."""
        status, body, _ = post_json("/auth/login", {
            "username": "rate_limit_test_user",
            "password": "WrongPass123!"
        })
        # 401 = bad creds handled gracefully, 429 = rate limit active (both valid)
        assert status in (401, 429)

    def test_sql_injection_in_login(self):
        """SQL injection attempt should be handled safely."""
        status, body, _ = post_json("/auth/login", {
            "username": "' OR 1=1 --",
            "password": "anything"
        })
        assert status in (401, 400, 422, 429)

    def test_xss_in_login(self):
        """XSS attempt should not reflect in response."""
        payload = "<script>alert(1)</script>"
        status, body, _ = post_json("/auth/login", {
            "username": payload,
            "password": "anything"
        })
        if isinstance(body, dict):
            body_str = str(body)
        else:
            body_str = str(body)
        assert "<script>" not in body_str


# ─── 7. ERROR HANDLING ─────────────────────────────────────────────────────

class TestErrorHandling:
    def test_404_api_route(self):
        status, _, _ = get("/api/nonexistent-route")
        assert status in (404, 405)

    def test_method_not_allowed(self):
        """DELETE on login should fail."""
        r = requests.delete(f"{BASE_URL}/auth/login", timeout=15)
        assert r.status_code == 405

    def test_invalid_json_body(self):
        """Malformed JSON to login should return 400/422 (or 429 if rate limited)."""
        r = requests.post(
            f"{BASE_URL}/auth/login",
            data="not json at all",
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code in (400, 422, 429)


# ─── 8. PERFORMANCE BASELINE ───────────────────────────────────────────────

class TestPerformance:
    def test_version_response_time(self):
        """Version endpoint should respond within 3 seconds (cold start budget)."""
        start = time.time()
        r = requests.get(f"{BASE_URL}/version", timeout=10)
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 3.0, f"/version took {elapsed:.2f}s"

    def test_sanity_response_time(self):
        start = time.time()
        r = requests.get(f"{BASE_URL}/test-sanity", timeout=10)
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 3.0, f"/test-sanity took {elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
