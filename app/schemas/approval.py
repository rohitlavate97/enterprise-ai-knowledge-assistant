"""ApprovalRequest Pydantic schemas for request validation."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequestBase(BaseModel):
    """Base validation schema for approval request."""

    action_type: str = Field(
        ...,
        max_length=100,
        description="The type of action requiring approval (e.g. 'delete_document')",
    )
    payload: dict[str, Any] = Field(
        ..., description="The JSON payload parameters containing entity IDs/arguments"
    )


class ApprovalRequestCreate(ApprovalRequestBase):
    """Schema for creating a new approval request."""

    pass


class ApprovalRequestReview(BaseModel):
    """Schema for reviewing (approving/rejecting) a pending request."""

    status: Literal["approved", "rejected"] = Field(
        ..., description="The review outcome status"
    )
    rejection_reason: str | None = Field(
        None, max_length=500, description="Reason for rejection (if status is rejected)"
    )
    comment: str | None = Field(None, description="Optional reviewer feedback comments")


class ApprovalRequestResponse(ApprovalRequestBase):
    """Serialized schema for returning approval request details."""

    id: UUID
    status: str
    requested_by_id: UUID
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    comment: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
