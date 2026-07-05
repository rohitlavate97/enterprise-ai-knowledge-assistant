"""Database Repository for Team models using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate


class TeamRepository:
    """Database repository layer for managing Team records."""

    async def get_by_id(self, db: AsyncSession, team_id: UUID) -> Team | None:
        """Retrieve a team by its unique UUID."""
        query = select(Team).where(Team.id == team_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Team | None:
        """Retrieve a team by its unique name."""
        query = select(Team).where(Team.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, team_in: TeamCreate) -> Team:
        """Create a new team record."""
        db_team = Team(
            name=team_in.name,
            description=team_in.description,
            department_id=team_in.department_id,
        )
        db.add(db_team)
        await db.commit()
        await db.refresh(db_team)
        return db_team

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Team]:
        """List teams with pagination."""
        query = select(Team).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, db: AsyncSession, db_team: Team, team_in: TeamUpdate
    ) -> Team:
        """Update a team record."""
        update_data = team_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_team, field, value)
        db.add(db_team)
        await db.commit()
        await db.refresh(db_team)
        return db_team

    async def delete(self, db: AsyncSession, db_team: Team) -> None:
        """Delete a team record."""
        await db.delete(db_team)
        await db.commit()


team_repo = TeamRepository()
