"""FastAPI router for AI Specialist Agents."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.research_agent import AgentDeps, ResearchAgentResponse, research_agent

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    """Schema representing request query for the Research Agent."""

    query: str = Field(min_length=1, description="Topic or question to research.")


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
    deps = AgentDeps(db=db, current_user=current_user)
    try:
        result = await research_agent.run(request.query, deps=deps)
        return result.output
    except Exception as err:
        logger.error("Research Agent execution failed: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research Agent failed: {str(err)}",
        ) from err
