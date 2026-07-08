"""FastAPI router for Chat sessions, Message streaming, and Memory management."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatQueryRequest,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    UserMemoryResponse,
)
from app.schemas.user import UserRole
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_chat_session(
    session_in: ChatSessionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Create a new multi-turn chat session."""
    return await chat_service.create_session(db, session_in, current_user.id)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all chat sessions for the authenticated user."""
    return await chat_service.list_sessions(db, current_user.id, skip=skip, limit=limit)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Retrieve a chat session and all its messages. Verifies user ownership."""
    db_session = await chat_service.get_session(db, session_id, current_user.id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied.",
        )
    return db_session


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def rename_chat_session(
    session_id: UUID,
    session_update: ChatSessionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Rename an existing chat session. Verifies user ownership."""
    db_session = await chat_service.rename_session(
        db, session_id, session_update, current_user.id
    )
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied.",
        )
    return db_session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a chat session. Verifies user ownership."""
    success = await chat_service.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied.",
        )


@router.post("/sessions/{session_id}/stream")
async def stream_chat(
    session_id: UUID,
    query_request: ChatQueryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """Send a message to the chat session and stream back the response chunks.

    Access Scopes for RAG context:
    - Standard Users are restricted to their own department
      (and optionally team) documents.
    - Admins can retrieve globally.
    """
    # Enforce RBAC tenant scoping rules for RAG
    if current_user.role != UserRole.ADMIN:
        # Standard user is locked to their own department
        target_department_id = current_user.department_id
        target_team_id = current_user.team_id
        if target_department_id is None:
            # If user has no department, they cannot view RAG context, pass None
            target_department_id = None
            target_team_id = None
    else:
        # Admins run globally by default
        target_department_id = None
        target_team_id = None

    generator = chat_service.stream_chat_response(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        user_message=query_request.message,
        limit=query_request.limit,
        threshold=query_request.threshold,
        department_id=target_department_id,
        team_id=target_team_id,
        background_tasks=background_tasks,
    )

    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/memory", response_model=UserMemoryResponse)
async def get_my_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Retrieve long-term memory for the authenticated user."""
    memory_data = await chat_service.get_user_memory(db, current_user.id)
    return UserMemoryResponse(user_id=current_user.id, memory_data=memory_data)


@router.put("/memory", response_model=UserMemoryResponse)
async def update_my_memory(
    memory_in: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Manually update or override long-term memory for the authenticated user."""
    return await chat_service.update_user_memory_manually(
        db, current_user.id, memory_in
    )
