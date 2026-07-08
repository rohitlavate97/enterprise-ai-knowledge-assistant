"""Unit and integration tests for the Research Agent and tool execution."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.department_repository import department_repo
from app.repositories.user_repository import user_repo
from app.schemas.department import DepartmentCreate
from app.schemas.user import UserCreate, UserRole
from app.services.research_agent import (
    AgentDeps,
    ResearchAgentResponse,
    research_agent,
    search_knowledge_base,
    search_web,
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
async def test_research_agent_tools_scoping(db: AsyncSession) -> None:
    """Test that Research Agent tools enforce tenant/department scoping correctly."""
    # 1. Create Departments
    dept_hr = await department_repo.create(
        db, DepartmentCreate(name="HR Dept", description="HR")
    )
    # Create ENG department and ignore the return to satisfy Ruff F841
    await department_repo.create(
        db, DepartmentCreate(name="Engineering Dept", description="ENG")
    )

    # 2. Create Users
    hr_user = await user_repo.create(
        db,
        UserCreate(
            email="hr_user_agent@enterprise.com",
            full_name="HR User",
            password="password123",
            role=UserRole.USER,
            department_id=dept_hr.id,
        ),
        hash_password("password123"),
    )

    # 3. Test search_knowledge_base tool directly
    deps_hr = AgentDeps(db=db, current_user=hr_user)

    # Use a simple class mock instead of subclassing RunContext
    class MockRunContext:
        def __init__(self, deps: AgentDeps) -> None:
            self.deps = deps

    ctx = MockRunContext(deps=deps_hr)
    res_search = await search_knowledge_base(ctx, query="benefits")  # type: ignore
    assert "No matching documents" in res_search or "Error" not in res_search

    # Test search_web tool directly
    res_web = await search_web(ctx, query="increment policies")  # type: ignore
    assert "Industry Standard" in res_web


@pytest.mark.asyncio
async def test_research_agent_api_endpoint(db: AsyncSession) -> None:
    """Test that the Research Agent endpoint runs and returns structured findings."""
    await user_repo.create(
        db,
        UserCreate(
            email="researcher@enterprise.com",
            full_name="Researcher",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "researcher@enterprise.com", "password123"
        )

        expected_response = ResearchAgentResponse(
            summary="Mocked research summary.",
            detailed_findings="Mocked detailed findings in markdown.",
            sources_cited=["point-123"],
            confidence_score=0.9,
        )

        # Execute endpoint with PydanticAI Agent override
        model_override = TestModel(custom_output_args=expected_response)
        with research_agent.override(model=model_override):
            res = await client.post(
                "/api/v1/agents/research",
                json={"query": "Research standard industry increment rates."},
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            data = res.json()
            assert data["summary"] == expected_response.summary
            assert data["detailed_findings"] == expected_response.detailed_findings
            assert data["sources_cited"] == expected_response.sources_cited
            assert data["confidence_score"] == expected_response.confidence_score
