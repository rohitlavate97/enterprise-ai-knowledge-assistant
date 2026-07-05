"""Pydantic schemas for Document models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    """Shared properties for Document schemas."""

    title: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)


class DocumentCreate(DocumentBase):
    """Properties to receive on Document creation."""

    file_path: str = Field(min_length=1, max_length=500)
    file_size: int = Field(gt=0)
    mime_type: str = Field(min_length=1, max_length=100)
    status: str = Field(default="pending", min_length=1, max_length=50)
    user_id: UUID
    department_id: UUID | None = None
    team_id: UUID | None = None


class DocumentUpdate(BaseModel):
    """Properties to receive on Document status or metadata update."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=50)


class DocumentResponse(DocumentBase):
    """Properties to return to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_size: int
    mime_type: str
    status: str
    user_id: UUID
    department_id: UUID | None
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SearchResultResponse(BaseModel):
    """Schema representing a single semantic search chunk match."""

    id: str
    score: float
    text: str
    document_id: UUID
    department_id: UUID | None = None
    team_id: UUID | None = None


class QueryRequest(BaseModel):
    """Schema representing a request to query the knowledge base."""

    question: str = Field(min_length=1)
    limit: int = Field(default=5, gt=0, le=20)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    department_id: UUID | None = None
    team_id: UUID | None = None


class QueryResponse(BaseModel):
    """Schema representing the reasoning answer alongside sources."""

    answer: str
    has_sufficient_context: bool
    confidence_score: float
    sources: list[SearchResultResponse]


