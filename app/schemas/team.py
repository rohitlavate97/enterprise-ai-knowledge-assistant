"""Pydantic schemas for Team models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    """Shared properties for Team schemas."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    department_id: UUID


class TeamCreate(TeamBase):
    """Properties to receive on Team creation."""

    pass


class TeamUpdate(BaseModel):
    """Properties to receive on Team update."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    department_id: UUID | None = None


class TeamResponse(TeamBase):
    """Properties to return to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
