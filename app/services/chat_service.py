"""Service layer coordinating Chat Sessions, Message streaming, and User Memory."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import chat_agent
from app.repositories.chat_repository import chat_repo
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate, ChatSessionUpdate
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class ChatService:
    """Service layer managing interactive multi-turn chat sessions and memories."""

    async def create_session(
        self, db: AsyncSession, session_in: ChatSessionCreate, user_id: UUID
    ) -> Any:
        """Create a new chat session."""
        return await chat_repo.create_session(db, session_in, user_id)

    async def list_sessions(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> Any:
        """List chat sessions for a user."""
        return await chat_repo.list_sessions_by_user(
            db, user_id, skip=skip, limit=limit
        )

    async def get_session(
        self, db: AsyncSession, session_id: UUID, user_id: UUID
    ) -> Any:
        """Retrieve a chat session with messages."""
        return await chat_repo.get_session_by_id(db, session_id, user_id)

    async def rename_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        session_update: ChatSessionUpdate,
        user_id: UUID,
    ) -> Any:
        """Rename a chat session title."""
        db_session = await chat_repo.get_session_by_id(db, session_id, user_id)
        if not db_session:
            return None
        return await chat_repo.update_session_title(
            db, db_session, session_update.title
        )

    async def delete_session(
        self, db: AsyncSession, session_id: UUID, user_id: UUID
    ) -> bool:
        """Delete a chat session."""
        db_session = await chat_repo.get_session_by_id(db, session_id, user_id)
        if not db_session:
            return False
        await chat_repo.delete_session(db, db_session)
        return True

    async def get_user_memory(self, db: AsyncSession, user_id: UUID) -> dict[str, Any]:
        """Get long-term memory for a user."""
        db_mem = await chat_repo.get_user_memory(db, user_id)
        return db_mem.memory_data if db_mem else {}

    async def update_user_memory_manually(
        self, db: AsyncSession, user_id: UUID, memory_data: dict[str, Any]
    ) -> Any:
        """Manually update user's long-term memory."""
        return await chat_repo.save_user_memory(db, user_id, memory_data)

    async def stream_chat_response(  # noqa: PLR0913
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        user_message: str,
        limit: int,
        threshold: float,
        department_id: UUID | None,
        team_id: UUID | None,
        background_tasks: BackgroundTasks,
    ) -> AsyncGenerator[str]:
        """Perform RAG retrieval, compile history/memories, stream response.

        Saves the resulting conversation message objects.
        """
        # 1. Verify session ownership
        db_session = await chat_repo.get_session_by_id(db, session_id, user_id)
        if not db_session:
            yield f"data: {json.dumps({'error': 'Chat session not found'})}\n\n"
            return

        # 2. Retrieve long-term memory
        memory_data = await self.get_user_memory(db, user_id)
        memory_str = ""
        if memory_data:
            memory_str = "Long-term User Memory:\n"
            if "preferences" in memory_data:
                memory_str += f"Preferences: {json.dumps(memory_data['preferences'])}\n"
            if "extracted_facts" in memory_data:
                memory_str += "Extracted Facts:\n"
                for fact in memory_data["extracted_facts"]:
                    memory_str += f"- {fact}\n"
            memory_str += "---\n"

        # 3. Compile Short-term Memory (last 10 messages from database)
        history_str = ""
        past_msgs = db_session.messages[-10:] if db_session.messages else []
        if past_msgs:
            history_str = "Conversation History:\n"
            for m in past_msgs:
                history_str += f"{m.role.capitalize()}: {m.content}\n"
            history_str += "---\n"

        # 4. RAG Vector DB Retrieval
        results = vector_service.search_similar_chunks(
            query=user_message,
            limit=limit,
            department_id=department_id,
            team_id=team_id,
        )
        sources = [r for r in results if r["score"] >= threshold]

        # Calculate heuristic confidence score (max similarity score or 0.0)
        confidence_score = max([s["score"] for s in sources]) if sources else 0.0

        context_str = ""
        if sources:
            context_str = "Retrieved Document Context:\n"
            for idx, s in enumerate(sources):
                src_info = (
                    f"[Source #{idx + 1}] Document ID: {s['document_id']}\n"
                    f"{s['text']}\n\n"
                )
                context_str += src_info
            context_str += "---\n"

        # 5. Compile Prompt
        prompt = (
            f"{memory_str}{history_str}{context_str}User: {user_message}\nAssistant:"
        )

        # 6. Save User Message to Database
        user_msg_create = ChatMessageCreate(role="user", content=user_message)
        await chat_repo.create_message(db, session_id, user_msg_create)

        # 7. Yield initial metadata event (sources, confidence_score)
        metadata_payload = {
            "type": "metadata",
            "citations": sources,
            "confidence_score": confidence_score,
        }
        yield f"data: {json.dumps(metadata_payload)}\n\n"

        # 8. Run streaming agent & yield tokens
        full_response_text = ""
        try:
            async with chat_agent.run_stream(prompt) as result:
                async for token in result.stream_text():
                    full_response_text += token
                    token_payload = {"type": "token", "content": token}
                    yield f"data: {json.dumps(token_payload)}\n\n"
        except Exception as e:
            logger.error("Error during token streaming: %s", str(e))
            err_payload = {"type": "token", "content": f" [Error: {str(e)}]"}
            yield f"data: {json.dumps(err_payload)}\n\n"
            full_response_text += f" [Error: {str(e)}]"

        # 9. Save Assistant Message to Database
        assistant_msg_create = ChatMessageCreate(
            role="assistant",
            content=full_response_text,
            citations=sources,
            confidence_score=confidence_score,
        )
        await chat_repo.create_message(db, session_id, assistant_msg_create)

        # 10. Schedule background task to extract/update long-term memory.
        # We pass user_id and user_message to keep extraction localized.
        background_tasks.add_task(
            self.extract_and_update_memory,
            db,
            user_id,
            user_message,
            full_response_text,
        )

        # Yield done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    async def extract_and_update_memory(
        self,
        db: AsyncSession,
        user_id: UUID,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Extract user preferences/facts in the background."""
        logger.info("Extracting memory for user: %s", user_id)
        logger.info("Assistant response length: %d", len(assistant_response))
        # Use heuristic rules to extract facts/preferences.
        # In a full agent context, we could call the LLM.
        try:
            db_mem = await chat_repo.get_user_memory(db, user_id)
            memory_data = (
                db_mem.memory_data
                if db_mem
                else {"preferences": {}, "extracted_facts": []}
            )

            # Simple rule-based extraction for testing and local dev
            extracted = False
            lower_msg = user_message.lower()
            if "i prefer" in lower_msg or "i like" in lower_msg:
                # E.g. "I prefer Python"
                pref = user_message.rsplit("prefer", maxsplit=1)[-1].strip(" .?!,")
                memory_data["preferences"]["last_stated_preference"] = pref
                extracted = True
            elif "my name is" in lower_msg:
                name = user_message.rsplit("name is", maxsplit=1)[-1].strip(" .?!,")
                memory_data["preferences"]["user_name"] = name
                extracted = True
            elif "remember that" in lower_msg:
                fact = user_message.rsplit("remember that", maxsplit=1)[-1].strip(
                    " .?!,"
                )
                if fact not in memory_data["extracted_facts"]:
                    memory_data["extracted_facts"].append(fact)
                extracted = True

            if extracted:
                await chat_repo.save_user_memory(db, user_id, memory_data)
                logger.info("Successfully updated user memory facts/preferences.")
        except Exception as e:
            logger.error("Error in background memory extraction: %s", str(e))


chat_service = ChatService()
