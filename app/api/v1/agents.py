"""FastAPI router for AI Specialist Agents."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.coordinator_agent import (
    CoordinatorResponse,
    CoordinatorState,
    coordinator_graph,
)
from app.services.document_agent import (
    AgentDeps as DocumentAgentDeps,
    DocumentAgentResponse,
    document_agent,
)
from app.services.research_agent import (
    AgentDeps as ResearchAgentDeps,
    ResearchAgentResponse,
    research_agent,
)

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    """Schema representing request query for the Research Agent."""

    query: str = Field(min_length=1, description="Topic or question to research.")


class DocumentAgentRequest(BaseModel):
    """Schema representing request query/command for the Document Agent."""

    query: str = Field(
        min_length=1, description="Command or query for the Document Agent."
    )


class CoordinatorRequest(BaseModel):
    """Schema representing request query/command for the Coordinator Agent."""

    query: str = Field(
        min_length=1, description="Command or query for the Coordinator Agent."
    )


@router.post("/research", response_model=ResearchAgentResponse)
async def run_research(
    request: ResearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Execute the Research Agent with context dependencies and tool-calling."""
    logger.info(
        "Executing Research Agent for user=%s, query='%s'",
        current_user.email,
        request.query,
    )
    deps = ResearchAgentDeps(db=db, current_user=current_user)
    try:
        result = await research_agent.run(request.query, deps=deps)
        return result.output
    except Exception as err:
        logger.error("Research Agent execution failed: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research Agent failed: {str(err)}",
        ) from err


@router.post("/document", response_model=DocumentAgentResponse)
async def run_document_agent(
    request: DocumentAgentRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Execute the Document Agent with context dependencies and tool-calling."""
    logger.info(
        "Executing Document Agent for user=%s, query='%s'",
        current_user.email,
        request.query,
    )
    deps = DocumentAgentDeps(db=db, current_user=current_user)
    try:
        result = await document_agent.run(request.query, deps=deps)
        return result.output
    except Exception as err:
        logger.error("Document Agent execution failed: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document Agent failed: {str(err)}",
        ) from err


@router.post("/coordinator", response_model=CoordinatorResponse)
async def run_coordinator_agent(
    request: CoordinatorRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Execute the Coordinator Agent LangGraph workflow to route queries."""
    logger.info(
        "Executing Coordinator Agent for user=%s, query='%s'",
        current_user.email,
        request.query,
    )
    initial_state: CoordinatorState = {
        "query": request.query,
        "db": db,
        "current_user": current_user,
        "next_agent": "",
        "routing_reason": "",
        "output": None,
    }
    try:
        final_state = await coordinator_graph.ainvoke(initial_state)
        output = final_state.get("output")
        if not output:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Coordinator Agent failed to produce an output state.",
            )
        return output
    except Exception as err:
        logger.error("Coordinator Agent execution failed: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coordinator Agent failed: {str(err)}",
        ) from err
