"""Integration and unit tests for Human-in-the-Loop Approval Gating."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai import RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.repositories.approval_repository import approval_repo
from app.repositories.document_repository import document_repo
from app.repositories.user_repository import user_repo
from app.schemas.approval import ApprovalRequestCreate
from app.schemas.document import DocumentCreate
from app.schemas.user import UserCreate, UserRole
from app.services.document_agent import AgentDeps, delete_document


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
async def test_document_deletion_submits_approval(db: AsyncSession) -> None:
    """Test that running the delete tool creates a pending request."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="approver_user@enterprise.com",
            full_name="Requester User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    doc = await document_repo.create(
        db,
        DocumentCreate(
            title="Secret Formulas.txt",
            filename="Secret Formulas.txt",
            file_path="storage/documents/secret_formulas.txt",
            file_size=120,
            mime_type="text/plain",
            status="completed",
            user_id=user.id,
        ),
    )

    # Invoke tool directly
    deps = AgentDeps(db=db, current_user=user)

    # We mock RunContext for direct tool invocation
    class MockContext(RunContext[AgentDeps]):
        def __init__(self, dependencies: AgentDeps):
            self.deps = dependencies

    ctx = MockContext(deps)

    res = await delete_document(ctx, str(doc.id))
    assert "pending administrator review" in res

    db.expunge_all()

    # Verify ApprovalRequest exists in DB
    requests = await approval_repo.list_by_user(db, user.id)
    assert len(requests) == 1
    assert requests[0].action_type == "delete_document"
    assert requests[0].status == "pending"
    assert requests[0].payload["document_id"] == str(doc.id)

    # Verify document still exists in DB (deletion was gated/blocked)
    db_doc = await document_repo.get_by_id(db, doc.id)
    assert db_doc is not None


@pytest.mark.asyncio
async def test_admin_approves_deletion(db: AsyncSession) -> None:
    """Test that Admin approval triggers document deletion execution."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="req_user@enterprise.com",
            full_name="Requester",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    admin = await user_repo.create(
        db,
        UserCreate(
            email="admin_approver@enterprise.com",
            full_name="Admin Reviewer",
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

    # Create pending request
    req_in = ApprovalRequestCreate(
        action_type="delete_document",
        payload={"document_id": str(doc.id)},
    )
    req = await approval_repo.create(db, req_in, user.id)

    # Call API to approve
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_auth_headers(
            client, "admin_approver@enterprise.com", "password123"
        )

        review_res = await client.post(
            f"/api/v1/approvals/{req.id}/review",
            json={"status": "approved", "comment": "Approved deletion"},
            headers=admin_headers,
        )
        assert review_res.status_code == status.HTTP_200_OK
        data = review_res.json()
        assert data["status"] == "approved"
        assert data["reviewed_by_id"] == str(admin.id)

        db.expunge_all()

        # Check DB states
        db_doc = await document_repo.get_by_id(db, doc.id)
        assert db_doc is None  # The document should be deleted now!


@pytest.mark.asyncio
async def test_admin_rejects_deletion(db: AsyncSession) -> None:
    """Test that Admin rejecting the request keeps the document intact."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="req_user2@enterprise.com",
            full_name="Requester 2",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    await user_repo.create(
        db,
        UserCreate(
            email="admin_approver2@enterprise.com",
            full_name="Admin Reviewer 2",
            password="password123",
            role=UserRole.ADMIN,
        ),
        hash_password("password123"),
    )

    doc = await document_repo.create(
        db,
        DocumentCreate(
            title="Sensitive Policy.txt",
            filename="Sensitive Policy.txt",
            file_path="storage/documents/sensitive_policy.txt",
            file_size=120,
            mime_type="text/plain",
            status="completed",
            user_id=user.id,
        ),
    )

    req_in = ApprovalRequestCreate(
        action_type="delete_document",
        payload={"document_id": str(doc.id)},
    )
    req = await approval_repo.create(db, req_in, user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_auth_headers(
            client, "admin_approver2@enterprise.com", "password123"
        )

        review_res = await client.post(
            f"/api/v1/approvals/{req.id}/review",
            json={
                "status": "rejected",
                "rejection_reason": "No policy deletions allowed",
            },
            headers=admin_headers,
        )
        assert review_res.status_code == status.HTTP_200_OK
        data = review_res.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "No policy deletions allowed"

        db.expunge_all()

        # Check DB states
        db_doc = await document_repo.get_by_id(db, doc.id)
        assert db_doc is not None  # Document remains intact


@pytest.mark.asyncio
async def test_non_admin_cannot_review(db: AsyncSession) -> None:
    """Test that a non-admin user cannot approve or reject request (RBAC validation)."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="standard_user_reviewer@enterprise.com",
            full_name="Standard User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    req_in = ApprovalRequestCreate(
        action_type="delete_document",
        payload={"document_id": "dummy-uuid"},
    )
    req = await approval_repo.create(db, req_in, user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "standard_user_reviewer@enterprise.com", "password123"
        )

        review_res = await client.post(
            f"/api/v1/approvals/{req.id}/review",
            json={"status": "approved"},
            headers=headers,
        )
        assert review_res.status_code == status.HTTP_403_FORBIDDEN
