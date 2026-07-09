"""Tests for Coordinator Agent routing and orchestration graph."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserRole
from app.services.coordinator_agent import (
    CoordinatorResponse,
    CoordinatorState,
    RoutingDecision,
    coordinator_graph,
    direct_agent,
    router_agent,
)
from app.services.document_agent import DocumentAgentResponse, document_agent
from app.services.research_agent import ResearchAgentResponse, research_agent


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
async def test_coordinator_routing_to_research(db: AsyncSession) -> None:
    """Test that the Coordinator routes queries to the Research Agent."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="coordinator_test1@enterprise.com",
            full_name="Test User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    initial_state = CoordinatorState(
        query="Research corporate wellness program trends.",
        db=db,
        current_user=user,
        next_agent="",
        routing_reason="",
        output=None,
    )

    routing_decision = RoutingDecision(
        next_agent="research",
        routing_reason="User query demands deep research on corporate wellness.",
    )
    research_res = ResearchAgentResponse(
        summary="Wellness summary.",
        detailed_findings="Detailed wellness findings.",
        sources_cited=["point-wellness"],
        confidence_score=0.85,
    )

    with (
        router_agent.override(model=TestModel(custom_output_args=routing_decision)),
        research_agent.override(model=TestModel(custom_output_args=research_res)),
    ):
        final_state = await coordinator_graph.ainvoke(initial_state)
        output = final_state["output"]
        assert output is not None
        assert output.selected_agent == "research"
        assert output.summary == "Wellness summary."
        assert "wellness" in output.detailed_findings.lower()
        assert output.documents_referenced == ["point-wellness"]
        assert output.confidence_score == 0.85


@pytest.mark.asyncio
async def test_coordinator_routing_to_document(db: AsyncSession) -> None:
    """Test that the Coordinator routes queries to the Document Agent."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="coordinator_test2@enterprise.com",
            full_name="Test User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    initial_state = CoordinatorState(
        query="List my uploaded documents.",
        db=db,
        current_user=user,
        next_agent="",
        routing_reason="",
        output=None,
    )

    routing_decision = RoutingDecision(
        next_agent="document",
        routing_reason="User query requests a listing of files.",
    )
    document_res = DocumentAgentResponse(
        response_summary="Found 2 documents.",
        document_details="Document list detail markdown.",
        documents_referenced=["doc-uuid-1", "doc-uuid-2"],
        operation_status="success",
    )

    with (
        router_agent.override(model=TestModel(custom_output_args=routing_decision)),
        document_agent.override(model=TestModel(custom_output_args=document_res)),
    ):
        final_state = await coordinator_graph.ainvoke(initial_state)
        output = final_state["output"]
        assert output is not None
        assert output.selected_agent == "document"
        assert output.summary == "Found 2 documents."
        assert output.documents_referenced == ["doc-uuid-1", "doc-uuid-2"]
        assert output.confidence_score == 1.0


@pytest.mark.asyncio
async def test_coordinator_routing_to_direct(db: AsyncSession) -> None:
    """Test that the Coordinator responds directly for greetings."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="coordinator_test3@enterprise.com",
            full_name="Test User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    initial_state = CoordinatorState(
        query="Hello, how are you?",
        db=db,
        current_user=user,
        next_agent="",
        routing_reason="",
        output=None,
    )

    routing_decision = RoutingDecision(
        next_agent="direct",
        routing_reason="User query is a standard greeting.",
    )

    with (
        router_agent.override(model=TestModel(custom_output_args=routing_decision)),
        direct_agent.override(
            model=TestModel(custom_output_text="Hello! I am ready to help.")
        ),
    ):
        final_state = await coordinator_graph.ainvoke(initial_state)
        output = final_state["output"]
        assert output is not None
        assert output.selected_agent == "direct"
        assert output.summary == "General conversation response."
        assert "Hello" in output.detailed_findings


@pytest.mark.asyncio
async def test_coordinator_api_endpoint(db: AsyncSession) -> None:
    """Test that the Coordinator endpoint functions and returns structured output."""
    await user_repo.create(
        db,
        UserCreate(
            email="coord_manager@enterprise.com",
            full_name="Coord Manager",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "coord_manager@enterprise.com", "password123"
        )

        expected_response = CoordinatorResponse(
            selected_agent="direct",
            routing_reason="API test routing.",
            summary="General conversation response.",
            detailed_findings="Mocked detailed markdown coordinator text.",
            documents_referenced=[],
            confidence_score=1.0,
        )

        # Execute endpoint with PydanticAI overrides on routing and direct agents
        with (
            router_agent.override(
                model=TestModel(
                    custom_output_args=RoutingDecision(
                        next_agent="direct", routing_reason="API test routing."
                    )
                )
            ),
            direct_agent.override(
                model=TestModel(
                    custom_output_text="Mocked detailed markdown coordinator text."
                )
            ),
        ):
            res = await client.post(
                "/api/v1/agents/coordinator",
                json={"query": "Hello!"},
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            data = res.json()
            assert data["selected_agent"] == expected_response.selected_agent
            assert data["summary"] == expected_response.summary
            assert data["detailed_findings"] == expected_response.detailed_findings
            assert (
                data["documents_referenced"] == expected_response.documents_referenced
            )
            assert data["confidence_score"] == expected_response.confidence_score
