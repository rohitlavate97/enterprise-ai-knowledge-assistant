"""Notification Pydantic schemas for request validation and response serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    """Base validation schema for notification."""

    title: str = Field(..., max_length=100, description="The alert title")
    message: str = Field(
        ..., max_length=500, description="The alert message detail content"
    )
    notification_type: str = Field(
        "info",
        max_length=50,
        description="Type of alert (e.g. info, success, warning, error, approval)",
    )


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""

    pass


class NotificationResponse(NotificationBase):
    """Serialized schema for returning notification details."""

    id: UUID
    user_id: UUID
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
