"""Pydantic schemas for administrative actions, analytics, and system monitoring."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Pydantic schema representing a serialized audit log entry."""

    id: UUID
    user_id: UUID | None = None
    action: str
    details: str
    payload: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemHealthResponse(BaseModel):
    """Pydantic schema for live system status and health parameters."""

    cpu_percent: float
    ram_percent: float
    db_connected: bool
    timestamp: datetime


class AdminAnalyticsResponse(BaseModel):
    """Pydantic schema for system-wide usage metrics and entity counts."""

    total_users: int
    total_documents: int
    total_workflows: int
    total_approvals: int
    total_storage_bytes: int
    document_status_counts: dict[str, int]
    workflow_status_counts: dict[str, int]
