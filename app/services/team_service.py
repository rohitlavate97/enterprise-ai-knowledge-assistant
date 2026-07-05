"""Team management business logic service."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.repositories.department_repository import department_repo
from app.repositories.team_repository import team_repo
from app.schemas.team import TeamCreate, TeamUpdate


class TeamService:
    """Service class for Team-related business operations."""

    async def create_team(self, db: AsyncSession, team_in: TeamCreate) -> Team:
        """Create a new team after checking name uniqueness and department existence."""
        # Verify department exists
        dep = await department_repo.get_by_id(db, team_in.department_id)
        if not dep:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with ID '{team_in.department_id}' not found.",
            )

        # Verify team name is unique
        existing = await team_repo.get_by_name(db, team_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{team_in.name}' already exists.",
            )

        return await team_repo.create(db, team_in)

    async def get_team(self, db: AsyncSession, team_id: UUID) -> Team:
        """Retrieve a team or raise 404 Not Found."""
        team = await team_repo.get_by_id(db, team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found.",
            )
        return team

    async def list_teams(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Team]:
        """List all teams with pagination support."""
        return await team_repo.list(db, skip=skip, limit=limit)

    async def update_team(
        self, db: AsyncSession, team_id: UUID, team_in: TeamUpdate
    ) -> Team:
        """Update a team checking name constraints and department presence."""
        db_team = await self.get_team(db, team_id)

        if team_in.department_id:
            dep = await department_repo.get_by_id(db, team_in.department_id)
            if not dep:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Department with ID '{team_in.department_id}' not found.",
                )

        if team_in.name and team_in.name != db_team.name:
            existing = await team_repo.get_by_name(db, team_in.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team with name '{team_in.name}' already exists.",
                )

        return await team_repo.update(db, db_team, team_in)

    async def delete_team(self, db: AsyncSession, team_id: UUID) -> None:
        """Delete a team."""
        db_team = await self.get_team(db, team_id)
        await team_repo.delete(db, db_team)


team_service = TeamService()
