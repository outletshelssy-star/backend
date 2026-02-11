def _login_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_company_id(client, auth_headers) -> int:
    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response.status_code == 200
    company_id = response.json()["company_id"]
    assert company_id is not None
    return company_id


def _create_block(client, auth_headers) -> int:
    response = client.post(
        "/api/v1/company-blocks/",
        json={
            "name": "Terminal Block",
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_admin_company(client, auth_headers) -> int:
    response = client.post(
        "/api/v1/companies/",
        json={
            "name": "Admin Co",
            "company_type": "client",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_company_terminal(client, auth_headers):
    block_id = _create_block(client, auth_headers)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal A",
            "is_active": True,
            "block_id": block_id,
            "admin_company_id": admin_company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Terminal A"
    assert data["is_active"] is True
    assert data["block_id"] == block_id
    assert data["owner_company_id"] > 0
    assert data["admin_company_id"] == admin_company_id
    assert data["created_by_user_id"] > 0


def test_list_company_terminals(client, auth_headers):
    block_id = _create_block(client, auth_headers)
    admin_company_id = _create_admin_company(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal List",
            "is_active": True,
            "block_id": block_id,
            "admin_company_id": admin_company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/company-terminals/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_company_terminal_by_id(client, auth_headers):
    block_id = _create_block(client, auth_headers)
    admin_company_id = _create_admin_company(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal B",
            "is_active": False,
            "block_id": block_id,
            "admin_company_id": admin_company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    terminal_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/company-terminals/{terminal_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Terminal B"


def test_company_terminals_requires_auth(client):
    response = client.get("/api/v1/company-terminals/")

    assert response.status_code == 401


def test_non_admin_cannot_access_company_terminals(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "User",
            "email": "terminaluser@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user_response.status_code == 201

    normal_headers = _login_headers(client, "terminaluser@test.com", "supersecret123")

    list_response = client.get(
        "/api/v1/company-terminals/",
        headers=normal_headers,
    )
    assert list_response.status_code == 403

    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Nope Terminal",
            "is_active": True,
            "block_id": 1,
            "admin_company_id": company_id,
        },
        headers=normal_headers,
    )
    assert create_response.status_code == 403


def test_get_company_terminal_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/company-terminals/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_invalid_admin_company(client, auth_headers):
    block_id = _create_block(client, auth_headers)
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Invalid Admin",
            "is_active": True,
            "block_id": block_id,
            "admin_company_id": 99999,
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_invalid_block(client, auth_headers):
    admin_company_id = _create_admin_company(client, auth_headers)
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Invalid Block",
            "is_active": True,
            "block_id": 99999,
            "admin_company_id": admin_company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 404
