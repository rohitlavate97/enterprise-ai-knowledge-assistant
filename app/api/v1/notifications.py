"""FastAPI router for user alerts and notifications."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.notification_repository import notification_repo
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[NotificationResponse])
async def list_my_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve notifications for the current authenticated user."""
    is_read_filter = False if unread_only else None
    return await notification_repo.list_by_user(
        db,
        user_id=current_user.id,
        is_read=is_read_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/{notif_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notif_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Mark a specific notification as read."""
    notif = await notification_repo.mark_as_read(db, notif_id, current_user.id)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied.",
        )
    return notif


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Mark all unread notifications for the current user as read."""
    await notification_repo.mark_all_as_read(db, current_user.id)
    return {"message": "All notifications marked as read."}
