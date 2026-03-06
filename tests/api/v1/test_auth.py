def _login(client, email: str = "admin@local.dev", password: str = "supersecret123"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


def test_login_success(client):
    response = _login(client)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20
    assert isinstance(data["refresh_token"], str)
    assert len(data["refresh_token"]) > 20


def test_login_wrong_password(client):
    response = _login(client, password="wrongpassword")

    assert response.status_code == 401


def test_login_wrong_email(client):
    response = _login(client, email="noexiste@test.com")

    assert response.status_code == 401


def test_login_inactive_user(client, auth_headers):
    # Crear usuario inactivo
    me_response = client.get("/api/v1/users/me", headers=auth_headers)
    company_id = me_response.json()["company_id"]

    client.post(
        "/api/v1/users/",
        json={
            "name": "Inactive",
            "last_name": "Auth",
            "email": "inactiveauth@test.com",
            "password": "supersecret123",
            "is_active": False,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    response = _login(client, email="inactiveauth@test.com")

    assert response.status_code == 403


def test_login_missing_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        data={},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


def test_refresh_token_success(client):
    login_data = _login(client).json()
    refresh_token = login_data["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_new_access_token_is_valid(client):
    login_data = _login(client).json()
    refresh_token = login_data["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert me_response.status_code == 200


def test_refresh_token_rotates(client):
    login_data = _login(client).json()
    old_refresh_token = login_data["refresh_token"]

    # Usar el refresh token → se genera uno nuevo
    client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})

    # El token antiguo ya no debe funcionar
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == 401


def test_refresh_token_invalid(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "token-completamente-invalido"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


def test_logout_success(client):
    login_data = _login(client).json()
    access_token = login_data["access_token"]

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204


def test_logout_invalidates_access_token(client):
    login_data = _login(client).json()
    access_token = login_data["access_token"]

    client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # El access_token anterior ya no debe funcionar
    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 401


def test_logout_invalidates_refresh_token(client):
    login_data = _login(client).json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # El refresh_token anterior ya no debe funcionar
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_logout_requires_auth(client):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401
