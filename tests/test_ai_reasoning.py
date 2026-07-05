"""Unit and integration tests for AI reasoning and PydanticAI integration."""

import pytest
from pydantic_ai.models.test import TestModel

from app.core.ai import AgentResponse, assistant_agent
from app.services.ai_service import ai_service


@pytest.mark.asyncio
async def test_ai_service_structured_answering() -> None:
    """Test that the AI service compiles prompt and returns AgentResponse."""
    question = "What is the standard salary increment?"
    context_chunks = [
        "The standard salary increment for HR employees is 5 percent annually."
    ]

    expected_response = AgentResponse(
        answer="The standard salary increment is 5 percent annually.",
        has_sufficient_context=True,
        confidence_score=0.95,
    )

    with assistant_agent.override(
        model=TestModel(custom_output_args=expected_response)
    ):
        res = await ai_service.answer_with_context(question, context_chunks)

        assert isinstance(res, AgentResponse)
        assert res.answer == expected_response.answer
        assert res.has_sufficient_context is True
        assert res.confidence_score == expected_response.confidence_score


@pytest.mark.asyncio
async def test_ai_service_insufficient_context() -> None:
    """Test that the agent flags when context is insufficient to answer."""
    question = "Who is the CEO of the company?"
    context_chunks = ["The office is located in San Francisco."]

    expected_response = AgentResponse(
        answer="I do not have enough information to answer who the CEO is.",
        has_sufficient_context=False,
        confidence_score=0.0,
    )

    with assistant_agent.override(
        model=TestModel(custom_output_args=expected_response)
    ):
        res = await ai_service.answer_with_context(question, context_chunks)

        assert isinstance(res, AgentResponse)
        assert res.has_sufficient_context is False
        assert res.confidence_score == 0.0
