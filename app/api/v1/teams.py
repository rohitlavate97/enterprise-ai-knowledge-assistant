"""FastAPI router for Team management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker
from app.core.database import get_db
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.schemas.user import UserRole
from app.services.team_service import team_service

router = APIRouter(prefix="/teams", tags=["teams"])

# Role check dependencies
admin_or_manager = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))
admin_only = Depends(RoleChecker([UserRole.ADMIN]))


@router.post(
    "/",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[admin_or_manager],
)
async def create_team(
    team_in: TeamCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Create a new team. Restricted to Admin and Manager roles."""
    return await team_service.create_team(db, team_in)


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all teams with pagination support."""
    return await team_service.list_teams(db, skip=skip, limit=limit)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Any:
    """Retrieve a specific team by its UUID."""
    return await team_service.get_team(db, team_id)


@router.put(
    "/{team_id}",
    response_model=TeamResponse,
    dependencies=[admin_or_manager],
)
async def update_team(
    team_id: UUID,
    team_in: TeamUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update team details. Restricted to Admin and Manager roles."""
    return await team_service.update_team(db, team_id, team_in)


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[admin_only],
)
async def delete_team(
    team_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a team. Restricted to Admin role only."""
    await team_service.delete_team(db, team_id)
