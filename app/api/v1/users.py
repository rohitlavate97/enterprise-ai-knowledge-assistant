"""FastAPI router for User management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserRole, UserUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """Retrieve a specific user's profile by ID. Requires authentication."""
    _ = current_user
    return await user_service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update user details.

    Rules:
    - Admin can update any user's profile, role, status, department, and team.
    - Standard users can only update their own profile and are blocked from
      changing their role, status, department, or team.
    """
    if current_user.role != UserRole.ADMIN:
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update other user profiles.",
            )
        # Prevent standard users from updating privileged fields
        if (
            user_in.role is not None
            or user_in.is_active is not None
            or user_in.department_id is not None
            or user_in.team_id is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Standard users cannot modify roles, status, "
                    "department, or team assignments."
                ),
            )

    return await user_service.update_user(db, user_id, user_in)
