"""Database Repository for Chat Sessions, Messages, and User Memory using SQLAlchemy."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession, UserMemory
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate


class ChatRepository:
    """Database repository layer for managing chat history and memory."""

    async def get_session_by_id(
        self, db: AsyncSession, session_id: UUID, user_id: UUID
    ) -> ChatSession | None:
        """Retrieve a chat session by ID, verifying user ownership."""
        query = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_session(
        self, db: AsyncSession, session_in: ChatSessionCreate, user_id: UUID
    ) -> ChatSession:
        """Create a new chat session for a user."""
        db_session = ChatSession(
            title=session_in.title,
            user_id=user_id,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session

    async def list_sessions_by_user(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ChatSession]:
        """List all chat sessions for a specific user, ordered by last updated."""
        query = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_session_title(
        self, db: AsyncSession, db_session: ChatSession, new_title: str
    ) -> ChatSession:
        """Update a chat session's title."""
        db_session.title = new_title
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session

    async def delete_session(self, db: AsyncSession, db_session: ChatSession) -> None:
        """Delete a chat session."""
        await db.delete(db_session)
        await db.commit()

    async def create_message(
        self, db: AsyncSession, session_id: UUID, message_in: ChatMessageCreate
    ) -> ChatMessage:
        """Create a new chat message under a session."""
        db_message = ChatMessage(
            session_id=session_id,
            role=message_in.role,
            content=message_in.content,
            citations=message_in.citations,
            confidence_score=message_in.confidence_score,
        )
        db.add(db_message)

        # Touch the parent session's updated_at timestamp
        query = select(ChatSession).where(ChatSession.id == session_id)
        result = await db.execute(query)
        db_session = result.scalar_one_or_none()
        if db_session:
            db.add(db_session)

        await db.commit()
        await db.refresh(db_message)
        return db_message

    async def get_user_memory(
        self, db: AsyncSession, user_id: UUID
    ) -> UserMemory | None:
        """Retrieve the user's long-term memory record."""
        query = select(UserMemory).where(UserMemory.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def save_user_memory(
        self, db: AsyncSession, user_id: UUID, memory_data: dict[str, Any]
    ) -> UserMemory:
        """Create or update the user's long-term memory."""
        db_memory = await self.get_user_memory(db, user_id)
        if db_memory:
            db_memory.memory_data = memory_data
            db_memory.updated_by = user_id
        else:
            db_memory = UserMemory(
                user_id=user_id,
                memory_data=memory_data,
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(db_memory)
        await db.commit()
        await db.refresh(db_memory)
        return db_memory


chat_repo = ChatRepository()
