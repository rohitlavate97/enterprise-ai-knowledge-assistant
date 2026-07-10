"""Integration and unit tests for the Notifications module."""

from unittest.mock import patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai import RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.approval_repository import approval_repo
from app.repositories.document_repository import document_repo
from app.repositories.notification_repository import notification_repo
from app.repositories.user_repository import user_repo
from app.repositories.workflow_repository import workflow_repo
from app.schemas.document import DocumentCreate
from app.schemas.notification import NotificationCreate
from app.schemas.user import UserCreate, UserRole
from app.schemas.workflow import WorkflowCreate, WorkflowTaskCreate
from app.services.document_agent import AgentDeps, delete_document
from app.services.workflow_engine import WorkflowEngineService, workflow_engine


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
async def test_notification_crud(db: AsyncSession) -> None:
    """Test standard database CRUD operations for notifications."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="notif_crud@enterprise.com",
            full_name="Notif User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    # 1. Create Notification
    notif_in = NotificationCreate(
        title="Welcome Alert",
        message="Thanks for signing up!",
        notification_type="info",
    )
    notif = await notification_repo.create(db, notif_in, user.id)
    assert notif.title == "Welcome Alert"
    assert notif.is_read is False

    # 2. List notifications
    notifs = await notification_repo.list_by_user(db, user.id)
    assert len(notifs) == 1
    assert notifs[0].title == "Welcome Alert"

    # 3. Mark single as read
    await notification_repo.mark_as_read(db, notif.id, user.id)
    db.expunge_all()
    notif_updated = await notification_repo.get_by_id(db, notif.id)
    assert notif_updated is not None
    assert notif_updated.is_read is True
    assert notif_updated.read_at is not None

    # 4. Mark all as read
    # Create another unread notification
    await notification_repo.create(
        db,
        NotificationCreate(
            title="Second Alert", message="Content", notification_type="warning"
        ),
        user.id,
    )
    await notification_repo.mark_all_as_read(db, user.id)
    db.expunge_all()
    unread_notifs = await notification_repo.list_by_user(db, user.id, is_read=False)
    assert len(unread_notifs) == 0


@pytest.mark.asyncio
async def test_notification_endpoints(db: AsyncSession) -> None:
    """Test notification HTTP REST API endpoints."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="notif_api@enterprise.com",
            full_name="Notif API User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    notif = await notification_repo.create(
        db,
        NotificationCreate(
            title="Endpoint Alert",
            message="Endpoint message",
            notification_type="info",
        ),
        user.id,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "notif_api@enterprise.com", "password123"
        )

        # GET all notifications
        res_list = await client.get("/api/v1/notifications/", headers=headers)
        assert res_list.status_code == status.HTTP_200_OK
        data_list = res_list.json()
        assert len(data_list) == 1
        assert data_list[0]["title"] == "Endpoint Alert"

        # POST read single
        res_read = await client.post(
            f"/api/v1/notifications/{notif.id}/read", headers=headers
        )
        assert res_read.status_code == status.HTTP_200_OK
        assert res_read.json()["is_read"] is True

        # POST read all
        res_read_all = await client.post(
            "/api/v1/notifications/read-all", headers=headers
        )
        assert res_read_all.status_code == status.HTTP_200_OK
        assert "marked as read" in res_read_all.json()["message"]


@pytest.mark.asyncio
async def test_notifications_integrated_with_approvals(db: AsyncSession) -> None:
    """Test notification triggers upon approval creation and review decision."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="req_notif@enterprise.com",
            full_name="Requester",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    admin = await user_repo.create(
        db,
        UserCreate(
            email="admin_notif@enterprise.com",
            full_name="Admin",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    doc = await document_repo.create(
        db,
        DocumentCreate(
            title="Formulas.txt",
            filename="Formulas.txt",
            file_path="storage/documents/formulas.txt",
            file_size=120,
            mime_type="text/plain",
            status="completed",
            user_id=user.id,
        ),
    )

    # 1. Trigger delete tool directly (creates approval + notifies admin)
    deps = AgentDeps(db=db, current_user=user)

    class MockContext(RunContext[AgentDeps]):
        def __init__(self, dependencies: AgentDeps):
            self.deps = dependencies

    ctx = MockContext(deps)
    await delete_document(ctx, str(doc.id))

    db.expunge_all()

    # Verify Admin received a notification
    admin_notifs = await notification_repo.list_by_user(db, admin.id)
    assert len(admin_notifs) == 1
    assert admin_notifs[0].notification_type == "approval"
    assert "New Approval Request" in admin_notifs[0].title

    # 2. Admin reviews/approves request (creates notification for requester)
    reqs = await approval_repo.list_by_user(db, user.id)
    assert len(reqs) == 1

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_auth_headers(
            client, "admin_notif@enterprise.com", "password123"
        )
        review_res = await client.post(
            f"/api/v1/approvals/{reqs[0].id}/review",
            json={"status": "approved", "comment": "Okay"},
            headers=admin_headers,
        )
        assert review_res.status_code == status.HTTP_200_OK

        db.expunge_all()

        # Verify requester received a notification
        user_notifs = await notification_repo.list_by_user(db, user.id)
        # Note: requester user_notifs might contain original uploads,
        # but filter by type approval
        app_notifs = [n for n in user_notifs if n.notification_type == "approval"]
        assert len(app_notifs) == 1
        assert "Approval Request Approved" in app_notifs[0].title


@pytest.mark.asyncio
async def test_notifications_integrated_with_workflows(db: AsyncSession) -> None:
    """Test notification trigger upon workflow completion."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_notif@enterprise.com",
            full_name="Workflow Owner",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    wf_in = WorkflowCreate(
        name="Notified Workflow",
        description="WF describing notification test",
        tasks=[
            WorkflowTaskCreate(
                name="Direct Task",
                task_type="direct",
                input_data={"query": "Hello"},
                step_number=1,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    # Run workflow
    def session_factory() -> AsyncSession:
        return db

    with patch.object(
        WorkflowEngineService, "execute_task_logic", return_value={"output": "Hi"}
    ):
        await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)  # type: ignore[arg-type]

    db.expunge_all()

    # Verify user received a workflow notification
    user_notifs = await notification_repo.list_by_user(db, user.id)
    wf_notifs = [n for n in user_notifs if n.notification_type == "workflow"]
    assert len(wf_notifs) == 1
    assert "Workflow Completed" in wf_notifs[0].title
    assert "Notified Workflow" in wf_notifs[0].message
