"""Pydantic schemas for Chat Sessions, Messages, and User Memory."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import SearchResultResponse


class ChatMessageBase(BaseModel):
    """Base schema for a chat message."""

    role: str = Field(
        description="Role of the message author: 'user', 'assistant', or 'system'."
    )
    content: str = Field(description="The textual content of the message.")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message in the database."""

    citations: list[dict[str, Any]] | None = None
    confidence_score: float | None = None


class ChatMessageResponse(ChatMessageBase):
    """Schema for returning a chat message to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    citations: list[SearchResultResponse] | None = None
    confidence_score: float | None = None
    created_at: datetime


class ChatSessionBase(BaseModel):
    """Base schema for a chat session."""

    title: str = Field(
        min_length=1, max_length=255, description="Title/topic of the chat session."
    )


class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""

    title: str = Field(default="New Chat", min_length=1, max_length=255)


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session's properties (e.g., renaming)."""

    title: str = Field(min_length=1, max_length=255)


class ChatSessionResponse(ChatSessionBase):
    """Schema for returning a chat session profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    """Detailed chat session response including message history."""

    messages: list[ChatMessageResponse] = []


class ChatQueryRequest(BaseModel):
    """Schema representing a new message request to send to the chat session."""

    message: str = Field(min_length=1, description="The user query.")
    limit: int = Field(
        default=5, gt=0, le=20, description="Retrieve up to this many context chunks."
    )
    threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for context retrieval.",
    )


class UserMemoryResponse(BaseModel):
    """Schema for returning a user's long-term memory."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    memory_data: dict[str, Any]
