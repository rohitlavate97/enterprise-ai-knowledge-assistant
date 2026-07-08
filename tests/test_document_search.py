"""Integration and API tests for tenant-scoped semantic search operations."""

import asyncio
import io
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.repositories.department_repository import department_repo
from app.repositories.user_repository import user_repo
from app.schemas.department import DepartmentCreate
from app.schemas.user import UserCreate, UserRole
from app.services.document_service import document_service
from app.services.vector_service import vector_service


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
async def test_end_to_end_tenant_scoped_search(  # noqa: PLR0915
    db: AsyncSession,
) -> None:
    """Test uploading documents across different departments and verifying scoping."""
    # 1. Create Departments
    dept_hr_in = DepartmentCreate(name="Human Resources", description="HR Department")
    dept_hr = await department_repo.create(db, dept_hr_in)

    dept_eng_in = DepartmentCreate(
        name="Engineering", description="Engineering Department"
    )
    dept_eng = await department_repo.create(db, dept_eng_in)

    # 2. Create Users
    await user_repo.create(
        db,
        UserCreate(
            email="hr@enterprise.com",
            full_name="HR Staff",
            password="password123",
            role=UserRole.USER,
            department_id=dept_hr.id,
        ),
        hash_password("password123"),
    )

    await user_repo.create(
        db,
        UserCreate(
            email="eng@enterprise.com",
            full_name="Eng Staff",
            password="password123",
            role=UserRole.USER,
            department_id=dept_eng.id,
        ),
        hash_password("password123"),
    )

    await user_repo.create(
        db,
        UserCreate(
            email="admin@enterprise.com",
            full_name="System Admin",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get Auth tokens
        hr_headers = await get_auth_headers(client, "hr@enterprise.com", "password123")
        eng_headers = await get_auth_headers(
            client, "eng@enterprise.com", "password123"
        )
        admin_headers = await get_auth_headers(
            client, "admin@enterprise.com", "password123"
        )

        # 3. Upload HR Document
        settings.UPLOAD_DIR = "storage/test_search_documents"
        hr_file_content = (
            b"The standard salary increment for HR employees is 5 percent annually."
        )
        hr_file_data = {
            "file": (
                "hr_policy.txt",
                io.BytesIO(hr_file_content),
                "text/plain",
            )
        }

        res_hr = await client.post(
            "/api/v1/documents/upload",
            files=hr_file_data,
            data={"department_id": str(dept_hr.id)},
            headers=hr_headers,
        )
        assert res_hr.status_code == status.HTTP_201_CREATED
        doc_hr_id = UUID(res_hr.json()["id"])

        # Poll until HR document processing completes
        for _ in range(30):
            res_status = await client.get(
                f"/api/v1/documents/{doc_hr_id}", headers=hr_headers
            )
            if res_status.json()["status"] == "completed":
                break
            await asyncio.sleep(0.5)

        # 4. Upload Engineering Document
        eng_file_content = (
            b"The production deployment branch is main. Deploy only after tests pass."
        )
        eng_file_data = {
            "file": (
                "eng_deploy.txt",
                io.BytesIO(eng_file_content),
                "text/plain",
            )
        }

        res_eng = await client.post(
            "/api/v1/documents/upload",
            files=eng_file_data,
            data={"department_id": str(dept_eng.id)},
            headers=eng_headers,
        )
        assert res_eng.status_code == status.HTTP_201_CREATED
        doc_eng_id = UUID(res_eng.json()["id"])

        # Poll until Eng document processing completes
        for _ in range(30):
            res_status = await client.get(
                f"/api/v1/documents/{doc_eng_id}", headers=eng_headers
            )
            if res_status.json()["status"] == "completed":
                break
            await asyncio.sleep(0.5)

        # 5. Search as HR staff (should only find HR policy content)
        res_search_hr = await client.get(
            "/api/v1/documents/search",
            params={"query": "salary increment"},
            headers=hr_headers,
        )
        assert res_search_hr.status_code == status.HTTP_200_OK
        hr_results = res_search_hr.json()
        assert len(hr_results) > 0
        assert all(UUID(r["document_id"]) == doc_hr_id for r in hr_results)

        # 6. Search as Engineering staff for HR info (should return empty list)
        res_search_eng_hr = await client.get(
            "/api/v1/documents/search",
            params={"query": "salary increment"},
            headers=eng_headers,
        )
        assert res_search_eng_hr.status_code == status.HTTP_200_OK
        assert len(res_search_eng_hr.json()) == 0

        # 7. Search as Engineering staff for deployment info
        res_search_eng = await client.get(
            "/api/v1/documents/search",
            params={"query": "deployment branch"},
            headers=eng_headers,
        )
        assert res_search_eng.status_code == status.HTTP_200_OK
        eng_results = res_search_eng.json()
        assert len(eng_results) > 0
        assert all(UUID(r["document_id"]) == doc_eng_id for r in eng_results)

        # 8. Search as Admin (global access)
        res_search_admin = await client.get(
            "/api/v1/documents/search",
            params={"query": "salary increment"},
            headers=admin_headers,
        )
        assert res_search_admin.status_code == status.HTTP_200_OK
        admin_results = res_search_admin.json()
        assert len(admin_results) > 0
        assert any(UUID(r["document_id"]) == doc_hr_id for r in admin_results)

        # Search with HR scope as Admin
        res_search_admin_hr = await client.get(
            "/api/v1/documents/search",
            params={
                "query": "salary increment",
                "department_id": str(dept_hr.id),
            },
            headers=admin_headers,
        )
        assert res_search_admin_hr.status_code == status.HTTP_200_OK
        assert all(
            UUID(r["document_id"]) == doc_hr_id for r in res_search_admin_hr.json()
        )

        # Clean up files on disk and Qdrant points
        vector_service.delete_document_points(doc_hr_id)
        vector_service.delete_document_points(doc_eng_id)

        # Unlink disk files
        for res in [res_hr.json(), res_eng.json()]:
            db_doc = await document_service.get_document(db, UUID(res["id"]))
            saved_file_path = Path(db_doc.file_path)
            if saved_file_path.exists():
                saved_file_path.unlink()
