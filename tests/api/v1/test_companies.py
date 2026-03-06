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
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


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

    # GET /companies/ is open to all authenticated users
    list_response = client.get(
        "/api/v1/companies/",
        headers=normal_headers,
    )
    assert list_response.status_code == 200

    # POST /companies/ requires admin or superadmin
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


# ---------------------------------------------------------------------------
# POST /companies/ — validaciones adicionales
# ---------------------------------------------------------------------------


def test_create_company_name_too_short(client, auth_headers):
    response = client.post(
        "/api/v1/companies/",
        json={"name": "A", "company_type": "client"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_invalid_type(client, auth_headers):
    response = client.post(
        "/api/v1/companies/",
        json={"name": "Some Co", "company_type": "invalid_type"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_name_is_normalized(client, auth_headers):
    response = client.post(
        "/api/v1/companies/",
        json={"name": "acme industries", "company_type": "client"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Acme Industries"


def test_create_company_requires_auth(client):
    response = client.post(
        "/api/v1/companies/",
        json={"name": "Auth Co", "company_type": "client"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /companies/ y GET /companies/{id} — auth e include
# ---------------------------------------------------------------------------


def test_get_company_by_id_requires_auth(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Auth Get Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.get(f"/api/v1/companies/{company_id}")

    assert response.status_code == 401


def test_list_companies_with_include_creator(client, auth_headers):
    response = client.get(
        "/api/v1/companies/?include=creator",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    company_with_creator = next((c for c in items if c["creator"] is not None), None)
    assert company_with_creator is not None
    assert "id" in company_with_creator["creator"]
    assert "name" in company_with_creator["creator"]


def test_get_company_with_include_creator(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Include Test Co", "company_type": "partner"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    # Sin include: creator es None
    plain = client.get(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert plain.status_code == 200
    assert plain.json()["creator"] is None

    # Con include=creator: creator está poblado
    with_include = client.get(
        f"/api/v1/companies/{company_id}?include=creator",
        headers=auth_headers,
    )
    assert with_include.status_code == 200
    creator = with_include.json()["creator"]
    assert creator is not None
    assert "id" in creator


# ---------------------------------------------------------------------------
# PUT /companies/{id}
# ---------------------------------------------------------------------------


def test_update_company(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Old Name Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "New Name Co", "is_active": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Co"
    assert data["is_active"] is False


def test_update_company_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/companies/99999",
        json={"name": "Does Not Exist"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_name_too_short(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Valid Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_company_invalid_type(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Type Test Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"company_type": "invalid_type"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_company_name_is_normalized(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Normalize Me Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "updated name co"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name Co"


def test_update_company_requires_auth(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Auth Update Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "New Name"},
    )

    assert response.status_code == 401


def test_non_admin_cannot_update_company(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Protected Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    me_response = client.get("/api/v1/users/me", headers=auth_headers)
    user_company_id = me_response.json()["company_id"]

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "Updater",
            "email": "normalupdater@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": user_company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(client, "normalupdater@test.com", "supersecret123")

    response = client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "Hacked Co"},
        headers=normal_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /companies/{id}
# ---------------------------------------------------------------------------


def test_delete_company(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Delete Me Co", "company_type": "partner"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/companies/{company_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deleted"
    assert payload["company"]["id"] == company_id

    get_response = client.get(
        f"/api/v1/companies/{company_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


def test_delete_company_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/companies/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_company_requires_auth(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Auth Delete Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/companies/{company_id}")

    assert response.status_code == 401


def test_non_admin_cannot_delete_company(client, auth_headers):
    create_response = client.post(
        "/api/v1/companies/",
        json={"name": "Protected Delete Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    me_response = client.get("/api/v1/users/me", headers=auth_headers)
    user_company_id = me_response.json()["company_id"]

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "Deleter",
            "email": "normaldeleter@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": user_company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(client, "normaldeleter@test.com", "supersecret123")

    response = client.delete(
        f"/api/v1/companies/{company_id}",
        headers=normal_headers,
    )

    assert response.status_code == 403
