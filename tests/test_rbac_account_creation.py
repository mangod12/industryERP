from tests.conftest import _make_client, create_test_user


def _registration_payload(username: str, role: str) -> dict:
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": "TestPass1!",
        "role": role,
    }


def test_boss_can_create_any_account_role(db):
    boss = create_test_user(db, role="Boss", username="rbac_boss")
    client = _make_client(db, boss)

    response = client.post("/auth/register", json=_registration_payload("boss_created_boss", "Boss"))

    assert response.status_code == 201
    assert response.json()["role"] == "Boss"


def test_software_supervisor_can_create_lower_privilege_worker_accounts(db):
    supervisor = create_test_user(db, role="Software Supervisor", username="rbac_supervisor")
    client = _make_client(db, supervisor)

    response = client.post("/auth/register", json=_registration_payload("supervisor_created_store", "Store Keeper"))

    assert response.status_code == 201
    assert response.json()["role"] == "Store Keeper"


def test_software_supervisor_cannot_create_boss_or_peer_accounts(db):
    supervisor = create_test_user(db, role="Software Supervisor", username="rbac_supervisor_limited")
    client = _make_client(db, supervisor)

    boss_response = client.post("/auth/register", json=_registration_payload("supervisor_created_boss", "Boss"))
    peer_response = client.post(
        "/auth/register",
        json=_registration_payload("supervisor_created_supervisor", "Software Supervisor"),
    )

    assert boss_response.status_code == 403
    assert boss_response.json()["detail"] == "Software Supervisor cannot create Boss accounts"
    assert peer_response.status_code == 403
    assert peer_response.json()["detail"] == "Software Supervisor cannot create Software Supervisor accounts"


def test_software_supervisor_cannot_bypass_hierarchy_with_role_alias(db):
    supervisor = create_test_user(db, role="Software Supervisor", username="rbac_supervisor_alias")
    client = _make_client(db, supervisor)

    response = client.post("/auth/register", json=_registration_payload("supervisor_alias_boss", "boss"))

    assert response.status_code == 403
    assert response.json()["detail"] == "Software Supervisor cannot create Boss accounts"


def test_worker_and_view_only_accounts_cannot_create_accounts(db):
    for role in ["Store Keeper", "QA Inspector", "Dispatch Operator", "Fabricator", "Painter", "User"]:
        user = create_test_user(db, role=role, username=f"rbac_{role.lower().replace(' ', '_')}")
        client = _make_client(db, user)

        response = client.post("/auth/register", json=_registration_payload(f"{user.username}_created_user", "User"))

        assert response.status_code == 403
