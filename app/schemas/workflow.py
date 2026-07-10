"""Pydantic validation schemas (DTOs) for Workflow and WorkflowTask."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowTaskBase(BaseModel):
    """Shared properties for a WorkflowTask."""

    name: str = Field(min_length=1, max_length=255)
    task_type: str = Field(
        min_length=1, max_length=100
    )  # e.g. "research", "document", "direct", "system"
    input_data: dict[str, Any] | None = Field(default=None)
    max_retries: int = Field(default=3, ge=0)
    retry_delay: int = Field(default=5, ge=0)  # delay in seconds
    scheduled_at: datetime | None = Field(default=None)
    depends_on_task_id: UUID | None = Field(default=None)
    conditional_routes: dict[str, Any] | None = Field(default=None)


class WorkflowTaskCreate(WorkflowTaskBase):
    """Properties to receive on WorkflowTask creation."""

    step_number: int = Field(ge=1)


class WorkflowTaskUpdate(BaseModel):
    """Properties to update an existing WorkflowTask."""

    status: str | None = Field(default=None, min_length=1, max_length=50)
    output_data: dict[str, Any] | None = Field(default=None)
    retry_count: int | None = Field(default=None, ge=0)
    scheduled_at: datetime | None = Field(default=None)


class WorkflowTaskResponse(WorkflowTaskBase):
    """Properties to return to the client for a WorkflowTask."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    status: str
    step_number: int
    retry_count: int
    output_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class WorkflowBase(BaseModel):
    """Shared properties for a Workflow."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class WorkflowCreate(WorkflowBase):
    """Properties to receive on Workflow creation."""

    tasks: list[WorkflowTaskCreate] = Field(min_length=1)


class WorkflowUpdate(BaseModel):
    """Properties to update an existing Workflow."""

    status: str | None = Field(default=None, min_length=1, max_length=50)


class WorkflowResponse(WorkflowBase):
    """Properties to return to the client for a Workflow."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    user_id: UUID
    tasks: list[WorkflowTaskResponse]
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
