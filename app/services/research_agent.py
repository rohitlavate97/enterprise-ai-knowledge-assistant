"""PydanticAI Research Agent configuration, tools, and execution service."""

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import ai_model
from app.core.vector_db import qdrant_client
from app.models.user import User
from app.schemas.user import UserRole
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependencies injected into the Research Agent execution context."""

    db: AsyncSession
    current_user: User


class ResearchAgentResponse(BaseModel):
    """Structured output format returned by the Research Agent."""

    summary: str = Field(
        description="A concise one-paragraph summary of the overall research findings."
    )
    detailed_findings: str = Field(
        description=(
            "Detailed analysis of findings structured professionally in Markdown."
        )
    )
    sources_cited: list[str] = Field(
        description=(
            "List of document IDs or point IDs cited as sources in this research."
        )
    )
    confidence_score: float = Field(
        description="Self-assessed confidence rating of the findings from 0.0 to 1.0."
    )


# Instantiate the Research Agent with structured output schema and dependency injections
research_agent = Agent(
    ai_model,
    deps_type=AgentDeps,
    output_type=ResearchAgentResponse,
    system_prompt=(
        "You are a specialized Research Agent. Your goal is to conduct deep, "
        "evidence-backed investigations over corporate documents and public knowledge. "
        "Follow these strict operational rules:\n"
        "1. Perform research using your available tools. Do not make up facts.\n"
        "2. Keep research strictly read-only. If the user requests any write action, "
        "modification, deletion, email sending, database write, or similar "
        "changes, you must refuse politely and explain that your scope is "
        "limited to read-only research.\n"
        "3. Explicitly cite source IDs/Point IDs for any claims you make."
    ),
)


@research_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDeps], query: str, limit: int = 5
) -> str:
    """Search vector database of corporate documents for similar chunks.

    Args:
        ctx: Execution context containing user credentials and session.
        query: Query keywords or sentence.
        limit: Max number of results.

    Returns:
        A text representation of matching document chunks with their IDs.
    """
    user = ctx.deps.current_user
    logger.info("Research Agent: Searching knowledge base for query='%s'", query)

    # Enforce RBAC tenant scoping rules
    if user.role != UserRole.ADMIN:
        dept_id = user.department_id
        team_id = user.team_id
        if dept_id is None:
            return "Error: User is not assigned to any department. Access denied."
    else:
        dept_id = None
        team_id = None

    try:
        results = vector_service.search_similar_chunks(
            query=query,
            limit=limit,
            department_id=dept_id,
            team_id=team_id,
        )
        if not results:
            return "No matching documents or context chunks found."

        output = []
        for idx, r in enumerate(results):
            output.append(
                f"[Source #{idx + 1}]\n"
                f"Chunk/Point ID: {r['id']}\n"
                f"Document ID: {r['document_id']}\n"
                f"Content: {r['text']}\n"
            )
        return "\n---\n".join(output)
    except Exception as err:
        logger.error("Research Agent search error: %s", str(err))
        return f"Error occurred during search: {str(err)}"


@research_agent.tool
async def read_document_chunk(ctx: RunContext[AgentDeps], point_id: str) -> str:
    """Retrieve the full text content of a specific chunk by its ID.

    Args:
        ctx: Execution context.
        point_id: Unique string ID of the vector point.

    Returns:
        The content details of the document chunk.
    """
    logger.info("Research Agent: Retrieving chunk content for point_id=%s", point_id)
    try:
        results = qdrant_client.retrieve(
            collection_name=vector_service.collection_name,
            ids=[point_id],
        )
        if not results:
            return f"Error: Document chunk with ID {point_id} not found."

        point = results[0]
        # Verify access credentials (multi-tenant check)
        user = ctx.deps.current_user
        if user.role != UserRole.ADMIN:
            point_dept = point.payload.get("department_id") if point.payload else None
            if point_dept and str(user.department_id) != str(point_dept):
                return "Error: Access denied. Chunk is outside your department scope."

        text = point.payload.get("text", "") if point.payload else ""
        doc_id = point.payload.get("document_id", "") if point.payload else ""
        return f"Document ID: {doc_id}\nContent: {text}"
    except Exception as err:
        logger.error("Research Agent retrieval error: %s", str(err))
        return f"Error retrieving document chunk: {str(err)}"


@research_agent.tool
async def search_web(ctx: RunContext[AgentDeps], query: str) -> str:
    """Query the web for public information/facts.

    Args:
        ctx: Execution context.
        query: Query search keywords.

    Returns:
        A summary of public information matching the query.
    """
    user_email = ctx.deps.current_user.email
    logger.info(
        "Research Agent: Web searching for query='%s' by %s",
        query,
        user_email,
    )
    # Return synthetic, deterministic facts for sandboxed execution
    return (
        f"Web Search Results for: '{query}'\n"
        "- Industry Standard: Increment guidelines suggest 3-5%.\n"
        "- Corporate Governance: Annual audit is recommended.\n"
        "- Public Knowledge: AI agents are shifting to tool-calling loops."
    )
