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


def test_create_company(client, auth_headers):
    response = client.post(
        "/api/v1/companies/",
        json={
            "name": "Acme Co",
            "company_type": "client",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Acme Co"
    assert data["company_type"] == "client"
    assert data["created_by_user_id"] > 0


def test_list_companies(client, auth_headers):
    response = client.get(
        "/api/v1/companies/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_company_by_id(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={
            "name": "Beta Co",
            "company_type": "partner",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/companies/{company_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Beta Co"


def test_companies_requires_auth(client):
    response = client.get("/api/v1/companies/")

    assert response.status_code == 401


def test_non_admin_cannot_access_companies(client, auth_headers):
    me_response = client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert me_response.status_code == 200
    company_id = me_response.json()["company_id"]
    assert company_id is not None

    create_user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "User",
            "email": "companyuser@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user_response.status_code == 201

    normal_headers = _login_headers(client, "companyuser@test.com", "supersecret123")

    list_response = client.get(
        "/api/v1/companies/",
        headers=normal_headers,
    )
    assert list_response.status_code == 403

    create_response = client.post(
        "/api/v1/companies/",
        json={
            "name": "Nope Co",
            "company_type": "client",
        },
        headers=normal_headers,
    )
    assert create_response.status_code == 403


def test_get_company_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/companies/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404
