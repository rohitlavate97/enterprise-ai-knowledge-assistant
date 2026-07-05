"""Tests for Department, Team, and User profile management API endpoints."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserRole


async def get_auth_headers(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    """Helper function to login a user and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_department_crud(db: AsyncSession) -> None:
    """Test full Department CRUD operations including RBAC restrictions."""
    # 1. Setup Admin and standard User
    admin_in = UserCreate(
        email="admin@enterprise.com",
        full_name="Admin User",
        password="password123",
        role=UserRole.ADMIN,
    )
    user_in = UserCreate(
        email="user@enterprise.com",
        full_name="Standard User",
        password="password123",
        role=UserRole.USER,
    )
    await user_repo.create(db, admin_in, hash_password("password123"))
    await user_repo.create(db, user_in, hash_password("password123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login users
        admin_headers = await get_auth_headers(
            client, "admin@enterprise.com", "password123"
        )
        user_headers = await get_auth_headers(
            client, "user@enterprise.com", "password123"
        )

        # Create Department (Failure - Standard User unauthorized)
        payload = {"name": "Engineering", "description": "Software development team"}
        res = await client.post(
            "/api/v1/departments/", json=payload, headers=user_headers
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # Create Department (Success - Admin)
        res = await client.post(
            "/api/v1/departments/", json=payload, headers=admin_headers
        )
        assert res.status_code == status.HTTP_201_CREATED
        dep_data = res.json()
        dep_id = dep_data["id"]
        assert dep_data["name"] == "Engineering"

        # Create Department (Failure - Duplicate Name)
        res = await client.post(
            "/api/v1/departments/", json=payload, headers=admin_headers
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

        # Get Department (Success)
        res = await client.get(f"/api/v1/departments/{dep_id}")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["name"] == "Engineering"

        # Update Department (Success - Admin)
        res = await client.put(
            f"/api/v1/departments/{dep_id}",
            json={"description": "Updated description"},
            headers=admin_headers,
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["description"] == "Updated description"

        # List Departments
        res = await client.get("/api/v1/departments/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()) == 1

        # Delete Department (Failure - Standard User)
        res = await client.delete(f"/api/v1/departments/{dep_id}", headers=user_headers)
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # Delete Department (Success - Admin)
        res = await client.delete(
            f"/api/v1/departments/{dep_id}", headers=admin_headers
        )
        assert res.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_team_crud_and_user_assignment(db: AsyncSession) -> None:
    """Test Team CRUD operations, constraint checks, and user assignments."""
    # 1. Setup Admin, User, and Department
    admin_in = UserCreate(
        email="admin@enterprise.com",
        full_name="Admin User",
        password="password123",
        role=UserRole.ADMIN,
    )
    user_in = UserCreate(
        email="user@enterprise.com",
        full_name="Standard User",
        password="password123",
        role=UserRole.USER,
    )
    admin_user = await user_repo.create(db, admin_in, hash_password("password123"))
    user_record = await user_repo.create(db, user_in, hash_password("password123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_auth_headers(
            client, "admin@enterprise.com", "password123"
        )
        user_headers = await get_auth_headers(
            client, "user@enterprise.com", "password123"
        )

        # Create Department first
        dep_res = await client.post(
            "/api/v1/departments/",
            json={"name": "HR Department", "description": "Human Resources"},
            headers=admin_headers,
        )
        dep_id = dep_res.json()["id"]

        # Create Team (Failure - Department Not Found)
        bad_team_payload = {
            "name": "Recruiting",
            "description": "Talent acquisition",
            "department_id": "00000000-0000-0000-0000-000000000000",
        }
        res = await client.post(
            "/api/v1/teams/", json=bad_team_payload, headers=admin_headers
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

        # Create Team (Success - Admin)
        team_payload = {
            "name": "Recruiting",
            "description": "Talent acquisition",
            "department_id": dep_id,
        }
        res = await client.post(
            "/api/v1/teams/", json=team_payload, headers=admin_headers
        )
        assert res.status_code == status.HTTP_201_CREATED
        team_data = res.json()
        team_id = team_data["id"]

        # User profile update (Success - Standard User updates own name)
        res = await client.put(
            f"/api/v1/users/{user_record.id}",
            json={"full_name": "Renamed Standard User"},
            headers=user_headers,
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["full_name"] == "Renamed Standard User"

        # User profile update (Failure - Standard User updates another user)
        res = await client.put(
            f"/api/v1/users/{admin_user.id}",
            json={"full_name": "Hacked name"},
            headers=user_headers,
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # User profile update (Failure - Standard User tries to assign team/department)
        res = await client.put(
            f"/api/v1/users/{user_record.id}",
            json={"team_id": team_id},
            headers=user_headers,
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # User Assignment (Success - Admin assigns User to Department and Team)
        res = await client.put(
            f"/api/v1/users/{user_record.id}",
            json={"department_id": dep_id, "team_id": team_id},
            headers=admin_headers,
        )
        assert res.status_code == status.HTTP_200_OK
        updated_user = res.json()
        assert updated_user["department_id"] == dep_id
        assert updated_user["team_id"] == team_id

        # Delete Team (Success - Admin)
        res = await client.delete(f"/api/v1/teams/{team_id}", headers=admin_headers)
        assert res.status_code == status.HTTP_204_NO_CONTENT
