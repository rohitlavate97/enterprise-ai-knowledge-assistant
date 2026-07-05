"""Integration and API tests for tenant-scoped RAG query operations."""

import asyncio
import io
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import AgentResponse, assistant_agent
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
async def test_end_to_end_rag_query(
    db: AsyncSession,
) -> None:  # noqa: PLR0915
    """Test RAG query workflow.

    Covers retrieval scoping, empty handling, and structured agent answers.
    """
    # 1. Create Departments
    dept_hr_in = DepartmentCreate(
        name="Human Resources", description="HR Department"
    )
    dept_hr = await department_repo.create(db, dept_hr_in)

    dept_eng_in = DepartmentCreate(
        name="Engineering", description="Engineering Department"
    )
    dept_eng = await department_repo.create(db, dept_eng_in)

    # 2. Create Users
    await user_repo.create(
        db,
        UserCreate(
            email="hr_user@enterprise.com",
            full_name="HR User",
            password="password123",
            role=UserRole.USER,
            department_id=dept_hr.id,
        ),
        hash_password("password123"),
    )

    await user_repo.create(
        db,
        UserCreate(
            email="eng_user@enterprise.com",
            full_name="Eng User",
            password="password123",
            role=UserRole.USER,
            department_id=dept_eng.id,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get Auth tokens
        hr_headers = await get_auth_headers(
            client, "hr_user@enterprise.com", "password123"
        )
        eng_headers = await get_auth_headers(
            client, "eng_user@enterprise.com", "password123"
        )

        # 3. Upload HR Document
        settings.UPLOAD_DIR = "storage/test_rag_documents"
        hr_file_content = (
            b"The standard salary increment for HR employees "
            b"is 5 percent annually."
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

        # 4. RAG Query as HR staff (matches HR document and invokes reasoning)
        expected_hr_res = AgentResponse(
            answer="The standard salary increment is 5 percent annually.",
            has_sufficient_context=True,
            confidence_score=0.95,
        )

        with assistant_agent.override(
            model=TestModel(custom_output_args=expected_hr_res)
        ):
            res_query_hr = await client.post(
                "/api/v1/documents/query",
                json={
                    "question": "What is the standard salary increment?",
                    "threshold": 0.2,
                },
                headers=hr_headers,
            )
            assert res_query_hr.status_code == status.HTTP_200_OK
            query_hr_data = res_query_hr.json()
            assert query_hr_data["answer"] == expected_hr_res.answer
            assert query_hr_data["has_sufficient_context"] is True
            assert len(query_hr_data["sources"]) > 0
            assert all(
                UUID(s["document_id"]) == doc_hr_id
                for s in query_hr_data["sources"]
            )

        # 5. RAG Query as Engineering staff (HR doc scoped out, should fail)
        res_query_eng = await client.post(
            "/api/v1/documents/query",
            json={
                "question": "What is the standard salary increment?",
                "threshold": 0.2,
            },
            headers=eng_headers,
        )
        assert res_query_eng.status_code == status.HTTP_200_OK
        query_eng_data = res_query_eng.json()
        assert query_eng_data["answer"] == "No relevant documents found."
        assert query_eng_data["has_sufficient_context"] is False
        assert len(query_eng_data["sources"]) == 0

        # Clean up files on disk and Qdrant points
        vector_service.delete_document_points(doc_hr_id)

        # Unlink disk files
        db_doc = await document_service.get_document(db, doc_hr_id)
        saved_file_path = Path(db_doc.file_path)
        if saved_file_path.exists():
            saved_file_path.unlink()
