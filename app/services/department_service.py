"""Department management business logic service."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.repositories.department_repository import department_repo
from app.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentService:
    """Service class for Department-related business operations."""

    async def create_department(
        self, db: AsyncSession, dep_in: DepartmentCreate
    ) -> Department:
        """Create a new department after checking name uniqueness."""
        existing = await department_repo.get_by_name(db, dep_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with name '{dep_in.name}' already exists.",
            )
        return await department_repo.create(db, dep_in)

    async def get_department(self, db: AsyncSession, dep_id: UUID) -> Department:
        """Retrieve a department or raise 404 Not Found."""
        dep = await department_repo.get_by_id(db, dep_id)
        if not dep:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found.",
            )
        return dep

    async def list_departments(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Department]:
        """List all departments with pagination support."""
        return await department_repo.list(db, skip=skip, limit=limit)

    async def update_department(
        self, db: AsyncSession, dep_id: UUID, dep_in: DepartmentUpdate
    ) -> Department:
        """Update a department checking name constraints."""
        db_dep = await self.get_department(db, dep_id)
        if dep_in.name and dep_in.name != db_dep.name:
            existing = await department_repo.get_by_name(db, dep_in.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department with name '{dep_in.name}' already exists.",
                )
        return await department_repo.update(db, db_dep, dep_in)

    async def delete_department(self, db: AsyncSession, dep_id: UUID) -> None:
        """Delete a department."""
        db_dep = await self.get_department(db, dep_id)
        await department_repo.delete(db, db_dep)


department_service = DepartmentService()
