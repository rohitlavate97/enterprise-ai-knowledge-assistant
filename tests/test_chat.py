"""Integration and API tests for Chat Session management, streaming, and user memory."""

import json
from uuid import UUID

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import chat_agent
from app.core.security import hash_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserRole


async def get_auth_headers(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    """Helper function to login a user and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_lifecycle_and_streaming(db: AsyncSession) -> None:
    """Test full chat session creation, renaming, streaming, and deletion.

    Includes testing of user memory and other features.
    """
    # 1. Create a test user
    await user_repo.create(
        db,
        UserCreate(
            email="chat_user@enterprise.com",
            full_name="Chat User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "chat_user@enterprise.com", "password123"
        )

        # 2. Create Chat Session
        create_res = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "Initial Title"},
            headers=headers,
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        session_id = UUID(create_res.json()["id"])
        assert create_res.json()["title"] == "Initial Title"

        # 3. Rename Chat Session
        rename_res = await client.put(
            f"/api/v1/chat/sessions/{session_id}",
            json={"title": "Updated Title"},
            headers=headers,
        )
        assert rename_res.status_code == status.HTTP_200_OK
        assert rename_res.json()["title"] == "Updated Title"

        # 4. Stream Message Response
        expected_text = "This is a mocked streaming response text."
        with chat_agent.override(model=TestModel(custom_output_text=expected_text)):
            async with client.stream(
                "POST",
                f"/api/v1/chat/sessions/{session_id}/stream",
                json={"message": "Hello, how does the policy work?"},
                headers=headers,
            ) as stream_res:
                assert stream_res.status_code == status.HTTP_200_OK

                # Consume stream
                lines = []
                async for line in stream_res.aiter_lines():
                    if line.startswith("data: "):
                        lines.append(json.loads(line[6:]))

                # Assert stream events
                assert len(lines) >= 3  # noqa: PLR2004
                assert lines[0]["type"] == "metadata"
                assert "confidence_score" in lines[0]
                assert "citations" in lines[0]

                # Reassemble tokens
                tokens = [
                    chunk["content"] for chunk in lines if chunk["type"] == "token"
                ]
                full_text = "".join(tokens)
                assert expected_text in full_text
                assert lines[-1]["type"] == "done"

        # 5. Fetch Session Detail and assert history has been saved
        detail_res = await client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=headers,
        )
        assert detail_res.status_code == status.HTTP_200_OK
        detail_data = detail_res.json()
        assert len(detail_data["messages"]) == 2  # noqa: PLR2004
        assert detail_data["messages"][0]["role"] == "user"
        assert (
            detail_data["messages"][0]["content"] == "Hello, how does the policy work?"
        )
        assert detail_data["messages"][1]["role"] == "assistant"
        assert expected_text in detail_data["messages"][1]["content"]

        # 6. Test User Memory
        mem_res = await client.get("/api/v1/chat/memory", headers=headers)
        assert mem_res.status_code == status.HTTP_200_OK

        # Manually update memory
        new_memory = {
            "preferences": {"theme": "dark"},
            "extracted_facts": ["User likes python"],
        }
        update_mem = await client.put(
            "/api/v1/chat/memory",
            json=new_memory,
            headers=headers,
        )
        assert update_mem.status_code == status.HTTP_200_OK
        assert update_mem.json()["memory_data"] == new_memory

        # 7. Delete Chat Session
        del_res = await client.delete(
            f"/api/v1/chat/sessions/{session_id}",
            headers=headers,
        )
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        # Try to fetch deleted session
        get_res = await client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=headers,
        )
        assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_chat_session_tenant_isolation(db: AsyncSession) -> None:
    """Verify that User B cannot access or modify User A's chat session."""
    # 1. Create two users
    await user_repo.create(
        db,
        UserCreate(
            email="user_a@enterprise.com",
            full_name="User A",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    await user_repo.create(
        db,
        UserCreate(
            email="user_b@enterprise.com",
            full_name="User B",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers_a = await get_auth_headers(
            client, "user_a@enterprise.com", "password123"
        )
        headers_b = await get_auth_headers(
            client, "user_b@enterprise.com", "password123"
        )

        # 2. Create Chat Session as User A
        create_res = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "User A Private Chat"},
            headers=headers_a,
        )
        session_id = UUID(create_res.json()["id"])

        # 3. Try to access session as User B
        get_res = await client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=headers_b,
        )
        assert get_res.status_code == status.HTTP_404_NOT_FOUND

        # 4. Try to rename session as User B
        rename_res = await client.put(
            f"/api/v1/chat/sessions/{session_id}",
            json={"title": "Hacked Title"},
            headers=headers_b,
        )
        assert rename_res.status_code == status.HTTP_404_NOT_FOUND

        # 5. Try to stream message to session as User B
        stream_res = await client.post(
            f"/api/v1/chat/sessions/{session_id}/stream",
            json={"message": "Hacked Message"},
            headers=headers_b,
        )
        # Note: the endpoint checks ownership in stream generator first.
        # Let's inspect the stream response content for error or check code.
        # If it returns 200 but first chunk has error, it matches chat response!
        # Let's verify by consuming the stream:
        lines = []
        async for line in stream_res.aiter_lines():
            if line.startswith("data: "):
                lines.append(json.loads(line[6:]))
        assert len(lines) == 1
        assert (
            "error" in lines[0] or "access denied" in lines[0].get("error", "").lower()
        )

        # 6. Try to delete session as User B
        del_res = await client.delete(
            f"/api/v1/chat/sessions/{session_id}",
            headers=headers_b,
        )
        assert del_res.status_code == status.HTTP_404_NOT_FOUND
