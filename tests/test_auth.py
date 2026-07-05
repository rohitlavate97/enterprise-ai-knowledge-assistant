"""Tests for authentication and authorization (RBAC) endpoints."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserRole


def test_password_utilities() -> None:
    """Test password hashing and verification functions."""
    pwd = "supersecretpassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


@pytest.mark.asyncio
async def test_register_user(db: AsyncSession) -> None:
    """Test user registration endpoint."""
    _ = db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "test@enterprise.com",
            "full_name": "Test User",
            "password": "securepassword123",
            "role": "user",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "test@enterprise.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "user"
        assert "id" in data


@pytest.mark.asyncio
async def test_login_and_access_protected(db: AsyncSession) -> None:
    """Test login credentials flow and accessing protected endpoints."""
    # Pre-register user in repo
    user_in = UserCreate(
        email="test@enterprise.com",
        full_name="Test User",
        password="securepassword123",
        role=UserRole.USER,
    )
    await user_repo.create(db, user_in, hash_password("securepassword123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@enterprise.com", "password": "securepassword123"},
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        access_token = tokens["access_token"]

        # Access Protected Endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        me_data = me_response.json()
        assert me_data["email"] == "test@enterprise.com"


@pytest.mark.asyncio
async def test_login_failure(db: AsyncSession) -> None:
    """Test login fails with invalid credentials."""
    _ = db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@enterprise.com",
                "password": "securepassword123",
            },
        )
        assert login_response.status_code == status.HTTP_400_BAD_REQUEST
        assert login_response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_refresh_token_flow(db: AsyncSession) -> None:
    """Test generating a new access token via refresh token."""
    user_in = UserCreate(
        email="test@enterprise.com",
        full_name="Test User",
        password="securepassword123",
        role=UserRole.USER,
    )
    await user_repo.create(db, user_in, hash_password("securepassword123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@enterprise.com", "password": "securepassword123"},
        )
        tokens = login_response.json()
        ref_token = tokens["refresh_token"]

        # Refresh token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ref_token},
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens


@pytest.mark.asyncio
async def test_role_based_access_control(db: AsyncSession) -> None:
    """Test RBAC blocks standard users and permits admins on restricted endpoints."""
    # 1. Create a standard User
    user_in = UserCreate(
        email="user@enterprise.com",
        full_name="Standard User",
        password="securepassword123",
        role=UserRole.USER,
    )
    await user_repo.create(db, user_in, hash_password("securepassword123"))

    # 2. Create an Admin User
    admin_in = UserCreate(
        email="admin@enterprise.com",
        full_name="Admin User",
        password="securepassword123",
        role=UserRole.ADMIN,
    )
    await user_repo.create(db, admin_in, hash_password("securepassword123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login standard User
        user_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@enterprise.com", "password": "securepassword123"},
        )
        user_token = user_login.json()["access_token"]

        # Login Admin User
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@enterprise.com", "password": "securepassword123"},
        )
        admin_token = admin_login.json()["access_token"]

        # User tries to access admin endpoint -> 403 Forbidden
        user_headers = {"Authorization": f"Bearer {user_token}"}
        user_res = await client.get("/api/v1/auth/admin-only", headers=user_headers)
        assert user_res.status_code == status.HTTP_403_FORBIDDEN

        # Admin tries to access admin endpoint -> 200 OK
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        admin_res = await client.get("/api/v1/auth/admin-only", headers=admin_headers)
        assert admin_res.status_code == status.HTTP_200_OK
        assert admin_res.json()["message"] == f"Hello Admin {admin_in.full_name}"
