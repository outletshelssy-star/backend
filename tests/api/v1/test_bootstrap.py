def test_bootstrap_disabled_in_test_env(client, auth_headers):
    response = client.post(
        "/api/v1/bootstrap/",
        json={"include_development_data": False},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "test" in response.json()["detail"].lower()


def test_bootstrap_requires_superadmin(client):
    response = client.post(
        "/api/v1/bootstrap/",
        json={"include_development_data": False},
    )
    assert response.status_code == 401
