# Milestone 13: AI Chat, Streaming Responses, and Session Memory

## Goal
Implement a fully functional interactive AI Chat system supporting:
- Session management (creating, retrieving, listing, and deleting chat sessions)
- Message storage (persisting user queries and AI responses with confidence scores and RAG citations)
- Conversation history tracking (Short-term memory scoped to the active session)
- Long-term User Memory (extracting and persisting user preferences/facts across sessions to personalize responses)
- Chunked real-time token streaming endpoints (`StreamingResponse` / Server-Sent Events)
- Secure, multi-tenant isolation (ensuring users can only access their own chat sessions and data)

## Status
- [x] Create `ChatSession`, `ChatMessage`, and `UserMemory` SQLAlchemy models (`app/models/chat.py`)
- [x] Register new models in `app/models/__init__.py` and generate database migrations using Alembic
- [x] Create Pydantic DTO validation schemas for chat sessions, messages, memory, and streaming events (`app/schemas/chat.py`)
- [x] Create repository layers (`ChatRepository`) and services (`ChatService`) to handle chat operations and long-term memory updates
- [x] Expose versioned endpoints under `/api/v1/chat` for listing sessions, retrieving messages, deleting sessions, and token streaming
- [x] Update frontend Streamlit UI to support interactive chat sessions, token streaming, memory inspector, and citation cards
- [x] Write unit, integration, and tenant-isolation tests for chat sessions, message histories, and streaming endpoints
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Explicit Memory Separation:** Short-term memory uses loaded message sequences for current session context. Long-term memory extracts facts and preferences (using background/inline extraction tasks) saved as JSON schema in `user_memories`, which are loaded and injected as system prompt constraints.
- **FastAPI StreamingResponse with Chunked JSON:** Token streaming is done via `StreamingResponse` using an async generator yielding SSE-like data formats (`data: {token: "...", confidence_score: 0.8, citations: [...]}`). This fits Streamlit's reading loops and allows parsing partial token packages.
- **Strict User Ownership / Multi-Tenant Isolation:** All chat endpoints verify user ownership (`session.user_id == current_user.id`) at the database repository and service boundaries, preventing unauthorized history access.

## Completed Tasks Record
* *Commit 31:* Create database models, schemas, repository layers, and Alembic migrations.
* *Commit 32:* Build chat streaming endpoints, service layers, and background memory extraction task.
* *Commit 33:* Update Streamlit UI, add unit and integration test suite, clean up Ruff/MyPy, and update CHANGELOG.
