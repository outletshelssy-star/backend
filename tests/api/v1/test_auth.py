def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@local.dev",
            "password": "supersecret123",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20
