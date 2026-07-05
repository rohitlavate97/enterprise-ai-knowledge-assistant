"""Database Repository for Department models using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentRepository:
    """Database repository layer for managing Department records."""

    async def get_by_id(self, db: AsyncSession, dep_id: UUID) -> Department | None:
        """Retrieve a department by its unique UUID."""
        query = select(Department).where(Department.id == dep_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Department | None:
        """Retrieve a department by its unique name."""
        query = select(Department).where(Department.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, dep_in: DepartmentCreate) -> Department:
        """Create a new department record."""
        db_dep = Department(name=dep_in.name, description=dep_in.description)
        db.add(db_dep)
        await db.commit()
        await db.refresh(db_dep)
        return db_dep

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Department]:
        """List departments with pagination."""
        query = select(Department).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, db: AsyncSession, db_dep: Department, dep_in: DepartmentUpdate
    ) -> Department:
        """Update a department record."""
        update_data = dep_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_dep, field, value)
        db.add(db_dep)
        await db.commit()
        await db.refresh(db_dep)
        return db_dep

    async def delete(self, db: AsyncSession, db_dep: Department) -> None:
        """Delete a department record."""
        await db.delete(db_dep)
        await db.commit()


department_repo = DepartmentRepository()
