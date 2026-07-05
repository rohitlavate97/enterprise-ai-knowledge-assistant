"""FastAPI router for Department management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker
from app.core.database import get_db
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.schemas.user import UserRole
from app.services.department_service import department_service

router = APIRouter(prefix="/departments", tags=["departments"])

# Role check dependencies
admin_or_manager = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))
admin_only = Depends(RoleChecker([UserRole.ADMIN]))


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[admin_or_manager],
)
async def create_department(
    dep_in: DepartmentCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Create a new department. Restricted to Admin and Manager roles."""
    return await department_service.create_department(db, dep_in)


@router.get("/", response_model=list[DepartmentResponse])
async def list_departments(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all departments with pagination support."""
    return await department_service.list_departments(db, skip=skip, limit=limit)


@router.get("/{dep_id}", response_model=DepartmentResponse)
async def get_department(
    dep_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Retrieve a specific department by its UUID."""
    return await department_service.get_department(db, dep_id)


@router.put(
    "/{dep_id}",
    response_model=DepartmentResponse,
    dependencies=[admin_or_manager],
)
async def update_department(
    dep_id: UUID,
    dep_in: DepartmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update department details. Restricted to Admin and Manager roles."""
    return await department_service.update_department(db, dep_id, dep_in)


@router.delete(
    "/{dep_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[admin_only],
)
async def delete_department(
    dep_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a department. Restricted to Admin role only."""
    await department_service.delete_department(db, dep_id)
