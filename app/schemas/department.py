"""Pydantic schemas for Department models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    """Shared properties for Department schemas."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class DepartmentCreate(DepartmentBase):
    """Properties to receive on Department creation."""

    pass


class DepartmentUpdate(BaseModel):
    """Properties to receive on Department update."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class DepartmentResponse(DepartmentBase):
    """Properties to return to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
