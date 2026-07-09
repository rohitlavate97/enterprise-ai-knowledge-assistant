"""PydanticAI Document Agent configuration, tools, and execution service."""

import contextlib
import logging
import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import ai_model
from app.models.document import Document
from app.models.user import User
from app.schemas.user import UserRole

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependencies injected into the Document Agent execution context."""

    db: AsyncSession
    current_user: User


class DocumentAgentResponse(BaseModel):
    """Structured output format returned by the Document Agent."""

    response_summary: str = Field(
        description=(
            "A concise summary of the document operations or status checks performed."
        )
    )
    document_details: str = Field(
        description=(
            "Detailed listing, metadata analysis, or status details "
            "formatted in Markdown."
        )
    )
    documents_referenced: list[str] = Field(
        description=(
            "List of document IDs or filenames processed, retrieved, or checked."
        )
    )
    operation_status: str = Field(
        description=(
            "Outcome status of the agent's operation "
            "(e.g. 'success', 'refused', 'not_found')."
        )
    )


# Instantiate the Document Agent with structured output schema and dependency injections
document_agent = Agent(
    ai_model,
    deps_type=AgentDeps,
    output_type=DocumentAgentResponse,
    system_prompt=(
        "You are a specialized Document Agent. Your goal is to manage, query, "
        "and inspect corporate document metadata and status records.\n"
        "Follow these strict operational rules:\n"
        "1. Retrieve document metadata using your available tools. "
        "Do not make up facts.\n"
        "2. Multi-tenant isolation: Only access documents within the "
        "user's department scope. Standard users cannot access documents "
        "outside their department. Admins can access all documents.\n"
        "3. Keep actions strictly read-only. If the user requests document "
        "deletion or any other destructive write action, you must use the "
        "delete_document tool, which will return a safe-gated refusal message. "
        "Explain that deletions are gated behind the Human-in-the-Loop "
        "approval workflow and are blocked."
    ),
)


@document_agent.tool
async def list_my_documents(ctx: RunContext[AgentDeps], limit: int = 50) -> str:
    """List available documents accessible to the current user.

    Args:
        ctx: Execution context containing user credentials and session.
        limit: Max number of results.

    Returns:
        A text representation of available documents with their IDs and titles.
    """
    user = ctx.deps.current_user
    db = ctx.deps.db
    logger.info("Document Agent: Listing documents for user %s", user.email)

    # Enforce RBAC tenant scoping rules
    if user.role != UserRole.ADMIN:
        if user.department_id is None:
            return "Error: User is not assigned to any department. Access denied."
        stmt = (
            select(Document)
            .where(Document.department_id == user.department_id)
            .limit(limit)
        )
    else:
        stmt = select(Document).limit(limit)

    try:
        result = await db.execute(stmt)
        docs = result.scalars().all()
        if not docs:
            return "No documents found."

        output = []
        for idx, doc in enumerate(docs):
            output.append(
                f"[Document #{idx + 1}]\n"
                f"ID: {doc.id}\n"
                f"Title: {doc.title}\n"
                f"Filename: {doc.filename}\n"
                f"File Size: {doc.file_size} bytes\n"
                f"MIME Type: {doc.mime_type}\n"
                f"Status: {doc.status}\n"
                f"Department ID: {doc.department_id}\n"
                f"Team ID: {doc.team_id}\n"
            )
        return "\n---\n".join(output)
    except Exception as err:
        logger.error("Document Agent list error: %s", str(err))
        return f"Error occurred during listing: {str(err)}"


@document_agent.tool
async def get_document_info(ctx: RunContext[AgentDeps], filename_or_id: str) -> str:
    """Retrieve detailed metadata for a specific document by its title, filename, or ID.

    Args:
        ctx: Execution context.
        filename_or_id: The document title, filename, or unique UUID.

    Returns:
        The detailed metadata of the document.
    """
    user = ctx.deps.current_user
    db = ctx.deps.db
    logger.info("Document Agent: Retrieving document info for: %s", filename_or_id)

    doc_id = None
    with contextlib.suppress(ValueError):
        doc_id = uuid.UUID(filename_or_id)

    if doc_id:
        stmt = select(Document).where(Document.id == doc_id)
    else:
        stmt = select(Document).where(
            (Document.title == filename_or_id) | (Document.filename == filename_or_id)
        )

    try:
        result = await db.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            return f"Document '{filename_or_id}' not found."

        # Enforce multi-tenant scoping
        if user.role != UserRole.ADMIN and doc.department_id != user.department_id:
            return "Error: Access denied. Document is outside your department scope."

        return (
            f"Document ID: {doc.id}\n"
            f"Title: {doc.title}\n"
            f"Filename: {doc.filename}\n"
            f"File Size: {doc.file_size} bytes\n"
            f"MIME Type: {doc.mime_type}\n"
            f"Status: {doc.status}\n"
            f"Department ID: {doc.department_id}\n"
            f"Team ID: {doc.team_id}\n"
            f"Created At: {doc.created_at}\n"
        )
    except Exception as err:
        logger.error("Document Agent get info error: %s", str(err))
        return f"Error occurred: {str(err)}"


@document_agent.tool
async def check_document_status(ctx: RunContext[AgentDeps], filename_or_id: str) -> str:
    """Check the ingestion or processing status of a specific document.

    Args:
        ctx: Execution context.
        filename_or_id: The document title, filename, or unique UUID.

    Returns:
        A status string detailing the current state of document processing.
    """
    user = ctx.deps.current_user
    db = ctx.deps.db
    logger.info("Document Agent: Checking status for: %s", filename_or_id)

    doc_id = None
    with contextlib.suppress(ValueError):
        doc_id = uuid.UUID(filename_or_id)

    if doc_id:
        stmt = select(Document).where(Document.id == doc_id)
    else:
        stmt = select(Document).where(
            (Document.title == filename_or_id) | (Document.filename == filename_or_id)
        )

    try:
        result = await db.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            return f"Document '{filename_or_id}' not found."

        # Enforce multi-tenant scoping
        if user.role != UserRole.ADMIN and doc.department_id != user.department_id:
            return "Error: Access denied. Document is outside your department scope."

        return (
            f"Document Title: {doc.title}\n"
            f"Document ID: {doc.id}\n"
            f"Processing Status: {doc.status}"
        )
    except Exception as err:
        logger.error("Document Agent status check error: %s", str(err))
        return f"Error occurred: {str(err)}"


@document_agent.tool
async def delete_document(ctx: RunContext[AgentDeps], filename_or_id: str) -> str:
    """Request deletion of a document from the system.

    Args:
        ctx: Execution context.
        filename_or_id: The document title, filename, or unique UUID.

    Returns:
        A response explaining whether the deletion succeeded or was refused.
    """
    user = ctx.deps.current_user
    db = ctx.deps.db
    logger.info("Document Agent: Deletion requested for: %s", filename_or_id)

    doc_id = None
    with contextlib.suppress(ValueError):
        doc_id = uuid.UUID(filename_or_id)

    if doc_id:
        stmt = select(Document).where(Document.id == doc_id)
    else:
        stmt = select(Document).where(
            (Document.title == filename_or_id) | (Document.filename == filename_or_id)
        )

    try:
        result = await db.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            return f"Document '{filename_or_id}' not found."

        # Enforce multi-tenant scoping
        if user.role != UserRole.ADMIN and doc.department_id != user.department_id:
            return "Error: Access denied. Document is outside your department scope."

        # Since Human-in-the-Loop Gating is not yet implemented
        # (scheduled in a future milestone), all deletion actions are blocked.
        return (
            f"Error: Deletion of document '{doc.title}' (ID: {doc.id}) "
            f"requested by user {user.email} is BLOCKED. Deletion is a "
            "write/destructive operation and requires explicit "
            "Human-in-the-Loop Approval Gating, which is currently "
            "pending backend integration."
        )
    except Exception as err:
        logger.error("Document Agent delete tool error: %s", str(err))
        return f"Error occurred: {str(err)}"
