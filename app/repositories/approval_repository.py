"""ApprovalRequest repository layer for database CRUD operations."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.schemas.approval import ApprovalRequestCreate


class ApprovalRepository:
    """Repository class managing database persistence for approvals."""

    async def create(
        self,
        db: AsyncSession,
        request_in: ApprovalRequestCreate,
        user_id: UUID,
    ) -> ApprovalRequest:
        """Create a new pending ApprovalRequest."""
        db_request = ApprovalRequest(
            action_type=request_in.action_type,
            payload=request_in.payload,
            status="pending",
            requested_by_id=user_id,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(db_request)
        await db.commit()
        await db.refresh(db_request)
        return db_request

    async def get_by_id(
        self, db: AsyncSession, request_id: UUID
    ) -> ApprovalRequest | None:
        """Fetch a specific ApprovalRequest by ID."""
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_all(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ApprovalRequest]:
        """List all approval requests, ordered by creation date descending."""
        stmt = (
            select(ApprovalRequest)
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ApprovalRequest]:
        """List all approval requests submitted by a specific user."""
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.requested_by_id == user_id)
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def list_pending(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ApprovalRequest]:
        """List all pending approval requests."""
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == "pending")
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_status(  # noqa: PLR0913
        self,
        db: AsyncSession,
        db_request: ApprovalRequest,
        status: str,
        reviewer_id: UUID,
        rejection_reason: str | None = None,
        comment: str | None = None,
    ) -> ApprovalRequest:
        """Update the review outcome of an ApprovalRequest."""
        db_request.status = status
        db_request.reviewed_by_id = reviewer_id
        db_request.reviewed_at = datetime.now(UTC)
        db_request.rejection_reason = rejection_reason
        db_request.comment = comment
        db_request.updated_by = reviewer_id

        db.add(db_request)
        await db.commit()
        await db.refresh(db_request)
        return db_request


approval_repo = ApprovalRepository()
