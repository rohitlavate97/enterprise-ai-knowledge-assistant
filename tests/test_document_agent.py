"""Unit and integration tests for the Document Agent and tool execution."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.department_repository import department_repo
from app.repositories.document_repository import document_repo
from app.repositories.user_repository import user_repo
from app.schemas.department import DepartmentCreate
from app.schemas.document import DocumentCreate
from app.schemas.user import UserCreate, UserRole
from app.services.document_agent import (
    AgentDeps,
    DocumentAgentResponse,
    check_document_status,
    delete_document,
    document_agent,
    get_document_info,
    list_my_documents,
)


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
async def test_document_agent_tools_scoping(db: AsyncSession) -> None:
    """Test that Document Agent tools enforce tenant/department scoping correctly."""
    # 1. Create Departments
    dept_hr = await department_repo.create(
        db, DepartmentCreate(name="HR Department", description="HR")
    )
    dept_eng = await department_repo.create(
        db, DepartmentCreate(name="Engineering Department", description="ENG")
    )

    # 2. Create Users
    hr_user = await user_repo.create(
        db,
        UserCreate(
            email="hr_agent_user@enterprise.com",
            full_name="HR User",
            password="password123",
            role=UserRole.USER,
            department_id=dept_hr.id,
        ),
        hash_password("password123"),
    )
    admin_user = await user_repo.create(
        db,
        UserCreate(
            email="admin_agent_user@enterprise.com",
            full_name="Admin User",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    # 3. Create Documents in respective departments
    doc_hr = await document_repo.create(
        db,
        DocumentCreate(
            title="HR Guidelines.txt",
            filename="HR Guidelines.txt",
            file_path="storage/documents/hr_guidelines.txt",
            file_size=100,
            mime_type="text/plain",
            status="completed",
            user_id=hr_user.id,
            department_id=dept_hr.id,
        ),
    )
    doc_eng = await document_repo.create(
        db,
        DocumentCreate(
            title="ENG Spec.txt",
            filename="ENG Spec.txt",
            file_path="storage/documents/eng_spec.txt",
            file_size=200,
            mime_type="text/plain",
            status="processing",
            user_id=admin_user.id,
            department_id=dept_eng.id,
        ),
    )

    # Mock RunContext equivalent helper
    class MockRunContext:
        def __init__(self, deps: AgentDeps) -> None:
            self.deps = deps

    # Test list_my_documents scoping:
    # HR user context
    ctx_hr = MockRunContext(deps=AgentDeps(db=db, current_user=hr_user))
    res_list_hr = await list_my_documents(ctx_hr)  # type: ignore
    assert "HR Guidelines.txt" in res_list_hr
    assert "ENG Spec.txt" not in res_list_hr

    # Admin user context
    ctx_admin = MockRunContext(deps=AgentDeps(db=db, current_user=admin_user))
    res_list_admin = await list_my_documents(ctx_admin)  # type: ignore
    assert "HR Guidelines.txt" in res_list_admin
    assert "ENG Spec.txt" in res_list_admin

    # Test get_document_info scoping:
    # HR user can retrieve HR doc info
    res_info_hr = await get_document_info(ctx_hr, str(doc_hr.id))  # type: ignore
    assert "HR Guidelines.txt" in res_info_hr
    assert "completed" in res_info_hr

    # HR user cannot retrieve ENG doc info (denied)
    res_info_eng_for_hr = await get_document_info(ctx_hr, str(doc_eng.id))  # type: ignore
    assert "Access denied" in res_info_eng_for_hr

    # Admin user can retrieve ENG doc info
    res_info_eng_for_admin = await get_document_info(ctx_admin, str(doc_eng.id))  # type: ignore
    assert "ENG Spec.txt" in res_info_eng_for_admin

    # Test check_document_status scoping:
    # HR user can check HR status
    res_status_hr = await check_document_status(ctx_hr, str(doc_hr.id))  # type: ignore
    assert "Status" in res_status_hr or "Status" in res_status_hr.title()
    assert "completed" in res_status_hr

    # HR user cannot check ENG status
    res_status_eng_for_hr = await check_document_status(ctx_hr, str(doc_eng.id))  # type: ignore
    assert "Access denied" in res_status_eng_for_hr

    # Test delete_document (should always return blocked refusal message)
    res_delete_hr = await delete_document(ctx_hr, str(doc_hr.id))  # type: ignore
    assert "pending administrator review" in res_delete_hr
    assert "Request ID" in res_delete_hr


@pytest.mark.asyncio
async def test_document_agent_api_endpoint(db: AsyncSession) -> None:
    """Test that the Document Agent endpoint runs and returns structured details."""
    await user_repo.create(
        db,
        UserCreate(
            email="doc_manager@enterprise.com",
            full_name="Doc Manager",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "doc_manager@enterprise.com", "password123"
        )

        expected_response = DocumentAgentResponse(
            response_summary="Mocked document operation summary.",
            document_details="Mocked markdown document details.",
            documents_referenced=["doc-uuid-123"],
            operation_status="success",
        )

        # Execute endpoint with PydanticAI Agent override
        model_override = TestModel(custom_output_args=expected_response)
        with document_agent.override(model=model_override):
            res = await client.post(
                "/api/v1/agents/document",
                json={"query": "List all my uploaded documents."},
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            data = res.json()
            assert data["response_summary"] == expected_response.response_summary
            assert data["document_details"] == expected_response.document_details
            assert (
                data["documents_referenced"] == expected_response.documents_referenced
            )
            assert data["operation_status"] == expected_response.operation_status
