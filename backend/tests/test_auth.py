import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["id"] == 1
    assert "created_at" in data["user"]
    assert "password_hash" not in data
    assert "password" not in data


def test_register_duplicate_email(client: TestClient) -> None:
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "password123",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_register_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "not-an-email",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_empty_name(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "   ",
            "email": "jane@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_login_success(client: TestClient, registered_user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert "user" not in data


def test_login_wrong_password(client: TestClient, registered_user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_auth_me_success(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "password_hash" not in data


def test_auth_me_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 403


def test_auth_me_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_users_get_me(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_users_patch_me(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

    me_response = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_response.json()["name"] == "Updated Name"


def test_users_patch_me_requires_auth(client: TestClient) -> None:
    response = client.patch("/api/v1/users/me", json={"name": "Updated Name"})

    assert response.status_code == 403


def test_register_normalizes_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "Jane@Example.COM",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "jane@example.com"


def test_login_normalizes_email(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "Jane@Example.COM",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
