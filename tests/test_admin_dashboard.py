"""Integration and unit tests for the Admin Dashboard and Live Health WebSockets."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.approval_repository import approval_repo
from app.repositories.audit_log_repository import audit_log_repo
from app.repositories.document_repository import document_repo
from app.repositories.user_repository import user_repo
from app.repositories.workflow_repository import workflow_repo
from app.schemas.approval import ApprovalRequestCreate
from app.schemas.document import DocumentCreate
from app.schemas.user import UserCreate, UserRole
from app.schemas.workflow import WorkflowCreate, WorkflowTaskCreate


async def get_auth_headers_and_token(
    client: AsyncClient, email: str, password: str
) -> tuple[dict[str, str], str]:
    """Helper function to login a user and return headers and raw token string."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


@pytest.mark.asyncio
async def test_admin_analytics(db: AsyncSession) -> None:
    """Test retrieving system analytics and verifying role-based gating."""
    _admin = await user_repo.create(
        db,
        UserCreate(
            email="admin_anal@enterprise.com",
            full_name="Admin User",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    user = await user_repo.create(
        db,
        UserCreate(
            email="user_anal@enterprise.com",
            full_name="Standard User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    # Add a document
    await document_repo.create(
        db,
        DocumentCreate(
            title="Sample.txt",
            filename="Sample.txt",
            file_path="storage/sample.txt",
            file_size=500,
            mime_type="text/plain",
            status="completed",
            user_id=user.id,
        ),
    )

    # Add a workflow
    wf_in = WorkflowCreate(
        name="Anal WF",
        tasks=[
            WorkflowTaskCreate(
                name="Task 1",
                task_type="direct",
                input_data={"query": "test"},
                step_number=1,
            )
        ],
    )
    await workflow_repo.create(db, wf_in, user.id)

    # Add an approval request
    req_in = ApprovalRequestCreate(
        action_type="delete_document",
        payload={"document_id": "dummy"},
    )
    await approval_repo.create(db, req_in, user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers, _ = await get_auth_headers_and_token(
            client, "admin_anal@enterprise.com", "password123"
        )
        user_headers, _ = await get_auth_headers_and_token(
            client, "user_anal@enterprise.com", "password123"
        )

        # Admin query
        res_admin = await client.get("/api/v1/admin/analytics", headers=admin_headers)
        assert res_admin.status_code == status.HTTP_200_OK
        data = res_admin.json()
        assert data["total_users"] == 2
        assert data["total_documents"] == 1
        assert data["total_workflows"] == 1
        assert data["total_approvals"] == 1
        assert data["total_storage_bytes"] == 500

        # Standard User query
        res_user = await client.get("/api/v1/admin/analytics", headers=user_headers)
        assert res_user.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_admin_audit_logs(db: AsyncSession) -> None:
    """Test writing and listing audit logs for administrative monitoring."""
    admin = await user_repo.create(
        db,
        UserCreate(
            email="admin_audit@enterprise.com",
            full_name="Admin Audit",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    # Write a test log
    await audit_log_repo.log(
        db,
        action="TEST_ACTION",
        details="Manual test details",
        user_id=admin.id,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers, _ = await get_auth_headers_and_token(
            client, "admin_audit@enterprise.com", "password123"
        )

        res_logs = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert res_logs.status_code == status.HTTP_200_OK
        data = res_logs.json()
        assert len(data) >= 1
        # The last or one of the logs is TEST_ACTION
        actions = [log["action"] for log in data]
        assert "TEST_ACTION" in actions
        assert "Manual test details" in [log["details"] for log in data]


@pytest.mark.asyncio
async def test_system_health_websocket(db: AsyncSession) -> None:
    """Test connecting to the health WebSocket and receiving metrics."""
    _admin = await user_repo.create(
        db,
        UserCreate(
            email="admin_ws@enterprise.com",
            full_name="Admin WS",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    _user = await user_repo.create(
        db,
        UserCreate(
            email="user_ws@enterprise.com",
            full_name="User WS",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, admin_token = await get_auth_headers_and_token(
            client, "admin_ws@enterprise.com", "password123"
        )
        _, user_token = await get_auth_headers_and_token(
            client, "user_ws@enterprise.com", "password123"
        )

    # 1. Standard user token should be rejected (403/closed)
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            f"/api/v1/admin/system-health/ws?token={user_token}"
        ) as ws, pytest.raises(Exception):  # noqa: B017
            _ = ws.receive_json()

        # 2. Missing token should be rejected
        with sync_client.websocket_connect(
            "/api/v1/admin/system-health/ws"
        ) as ws, pytest.raises(Exception):  # noqa: B017
            _ = ws.receive_json()

        # 3. Admin token should succeed and stream status
        with sync_client.websocket_connect(
            f"/api/v1/admin/system-health/ws?token={admin_token}"
        ) as ws:
            msg = ws.receive_json()
            assert "cpu_percent" in msg
            assert "ram_percent" in msg
            assert "db_connected" in msg
            assert msg["db_connected"] is True
            ws.close()
