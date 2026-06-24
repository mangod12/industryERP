from backend_core.app.security import hash_password, verify_password


def test_password_hashes_are_salted_and_not_plaintext():
    password = "SecurityPass1!"

    first = hash_password(password)
    second = hash_password(password)

    assert first != password
    assert second != password
    assert first != second
    assert first.startswith("$2")
    assert second.startswith("$2")
    assert verify_password(password, first)
    assert verify_password(password, second)


def test_security_headers_are_set(client):
    response = client.get("/version", headers={"x-forwarded-proto": "https"})

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_cookie_only_auth_is_rejected(client):
    response = client.get("/dashboard/enhanced-summary", cookies={"kb_token": "fake"})

    assert response.status_code == 401


def test_login_payload_bounds_are_enforced(client):
    response = client.post(
        "/auth/login",
        json={"username": "a" * 151, "password": "SecurityPass1!"},
    )

    assert response.status_code == 400


def test_registration_rejects_malformed_username(boss_client):
    response = boss_client.post(
        "/auth/register",
        json={
            "username": "bad username<script>",
            "email": "bad-user@example.test",
            "password": "SecurityPass1!",
            "role": "User",
        },
    )

    assert response.status_code == 422
