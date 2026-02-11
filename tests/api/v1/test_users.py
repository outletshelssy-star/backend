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


def test_create_user(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "willy@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Willy"
    assert data["last_name"] == "Corzo"
    assert data["email"] == "willy@test.com"
    assert data["is_active"] is True

    # defaults
    assert data["user_type"] == "user"
    assert data["photo_url"] is None
    assert data["company_id"] is not None


def test_create_user_duplicate_email(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    payload = {
        "name": "Willy",
        "last_name": "Corzo",
        "email": "dup@test.com",
        "password": "supersecret123",
        "is_active": True,
        "company_id": company_id,
    }

    response1 = client.post(
        "/api/v1/users/",
        json=payload,
        headers=auth_headers,
    )
    assert response1.status_code == 201

    response2 = client.post(
        "/api/v1/users/",
        json=payload,
        headers=auth_headers,
    )
    assert response2.status_code == 409
    assert response2.json()["detail"] == "Email already exists"


def test_create_user_name_too_short(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "W",
            "last_name": "Corzo",
            "email": "short@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_last_name_too_short(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "C",
            "email": "lastname@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_invalid_email(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "not-an-email",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_without_password(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "nopass@test.com",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_invalid_photo_url(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "photo@test.com",
            "password": "supersecret123",
            "photo_url": "notaurl",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_password_not_returned(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "secure@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    data = response.json()

    assert "password" not in data
    assert "password_hash" not in data


def test_create_user_invalid_user_type(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Willy",
            "last_name": "Corzo",
            "email": "role@test.com",
            "password": "supersecret123",
            "user_type": "godmode",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_user_requires_company(client, auth_headers):
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "No",
            "last_name": "Company",
            "email": "nocompany@test.com",
            "password": "supersecret123",
            "is_active": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_list_users(client, auth_headers):
    response = client.get(
        "/api/v1/users/",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1

    user = data["items"][0]
    assert "id" in user
    assert "email" in user
    assert "password" not in user
    assert "password_hash" not in user


def test_get_user_by_id(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    # crear usuario
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Ana",
            "last_name": "Perez",
            "email": "ana@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    user_id = response.json()["id"]

    # obtener usuario
    response = client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ana@test.com"


def test_get_me(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/users/",
        json={
            "name": "User",
            "last_name": "Me",
            "email": "me@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "me@test.com",
            "password": "supersecret123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["is_active"] is True


def test_update_me(client, auth_headers):
    response = client.put(
        "/api/v1/users/me",
        json={
            "name": "Nuevo Nombre",
            "last_name": "Nuevo Apellido",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nuevo Nombre"
    assert data["last_name"] == "Nuevo Apellido"


def test_admin_can_update_user(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/users/",
        json={
            "name": "User",
            "last_name": "ToUpdate",
            "email": "update@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"user_type": "admin"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_type"] == "admin"


def test_update_my_password(client, auth_headers):
    response = client.put(
        "/api/v1/users/me/password",
        json={
            "current_password": "supersecret123",
            "new_password": "newsupersecret456",
        },
        headers=auth_headers,
    )

    assert response.status_code == 204


def test_update_my_password_wrong_current(client, auth_headers):
    response = client.put(
        "/api/v1/users/me/password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newsupersecret456",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_list_users_requires_auth(client):
    response = client.get("/api/v1/users/")

    assert response.status_code == 401


def test_get_me_requires_auth(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_update_me_requires_auth(client):
    response = client.put(
        "/api/v1/users/me",
        json={"name": "No Auth"},
    )

    assert response.status_code == 401


def test_update_my_password_requires_auth(client):
    response = client.put(
        "/api/v1/users/me/password",
        json={
            "current_password": "supersecret123",
            "new_password": "newsupersecret456",
        },
    )

    assert response.status_code == 401


def test_non_admin_cannot_access_admin_endpoints(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "User",
            "email": "normal@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    normal_headers = _login_headers(client, "normal@test.com", "supersecret123")

    list_response = client.get(
        "/api/v1/users/",
        headers=normal_headers,
    )
    assert list_response.status_code == 403

    create_admin_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Another",
            "last_name": "User",
            "email": "another@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=normal_headers,
    )
    assert create_admin_response.status_code == 403

    target_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Target",
            "last_name": "User",
            "email": "target@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert target_response.status_code == 201
    target_id = target_response.json()["id"]

    update_response = client.put(
        f"/api/v1/users/{target_id}",
        json={"user_type": "admin"},
        headers=normal_headers,
    )
    assert update_response.status_code == 403


def test_get_user_by_id_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/users/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_me_name_too_short(client, auth_headers):
    response = client.put(
        "/api/v1/users/me",
        json={"name": "W"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_me_last_name_too_short(client, auth_headers):
    response = client.put(
        "/api/v1/users/me",
        json={"last_name": "C"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_me_invalid_photo_url(client, auth_headers):
    response = client.put(
        "/api/v1/users/me",
        json={"photo_url": "notaurl"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_my_password_changes_login(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Pass",
            "last_name": "Change",
            "email": "passchange@test.com",
            "password": "oldpassword123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    user_headers = _login_headers(client, "passchange@test.com", "oldpassword123")

    update_response = client.put(
        "/api/v1/users/me/password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
        },
        headers=user_headers,
    )
    assert update_response.status_code == 204

    old_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": "passchange@test.com",
            "password": "oldpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": "passchange@test.com",
            "password": "newpassword456",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert new_login.status_code == 200


def test_list_users_filter_is_active(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    active_email = "active@test.com"
    inactive_email = "inactive@test.com"

    response_active = client.post(
        "/api/v1/users/",
        json={
            "name": "Active",
            "last_name": "User",
            "email": active_email,
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response_active.status_code == 201

    response_inactive = client.post(
        "/api/v1/users/",
        json={
            "name": "Inactive",
            "last_name": "User",
            "email": inactive_email,
            "password": "supersecret123",
            "is_active": False,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response_inactive.status_code == 201

    list_active = client.get(
        "/api/v1/users/?is_active=true",
        headers=auth_headers,
    )
    assert list_active.status_code == 200
    active_items = list_active.json().get("items", [])
    active_emails = {item["email"] for item in active_items}
    assert active_email in active_emails
    assert inactive_email not in active_emails

    list_inactive = client.get(
        "/api/v1/users/?is_active=false",
        headers=auth_headers,
    )
    assert list_inactive.status_code == 200
    inactive_items = list_inactive.json().get("items", [])
    inactive_emails = {item["email"] for item in inactive_items}
    assert inactive_email in inactive_emails
    assert active_email not in inactive_emails


def test_delete_user_without_activity_deletes(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Delete",
            "last_name": "Me",
            "email": "delete@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deleted"
    assert payload["user"] is None

    get_response = client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


def test_delete_user_with_activity_deactivates(client, auth_headers, session):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Deactivate",
            "last_name": "Me",
            "email": "deactivate@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    activity_company = Company(
        name="User Activity Co",
        company_type=CompanyType.partner,
        created_by_user_id=user_id,
    )
    session.add(activity_company)
    session.commit()

    delete_response = client.delete(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deactivated"
    assert payload["user"]["is_active"] is False

    get_response = client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


def test_admin_cannot_delete_superadmin(client, auth_headers, session):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Admin",
            "last_name": "User",
            "email": "adminuser@test.com",
            "password": "supersecret123",
            "user_type": "admin",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    admin_headers = _login_headers(client, "adminuser@test.com", "supersecret123")
    superadmin = session.exec(
        select(User).where(User.user_type == UserType.superadmin)
    ).first()
    assert superadmin is not None

    delete_response = client.delete(
        f"/api/v1/users/{superadmin.id}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 403
from sqlmodel import select

from app.models.company import Company
from app.models.enums import CompanyType, UserType
from app.models.user import User
