"""Notification repository layer for database CRUD operations."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate


class NotificationRepository:
    """Repository class managing database persistence for notifications."""

    async def create(
        self,
        db: AsyncSession,
        notification_in: NotificationCreate,
        user_id: UUID,
    ) -> Notification:
        """Create a new Notification record."""
        db_notif = Notification(
            user_id=user_id,
            title=notification_in.title,
            message=notification_in.message,
            notification_type=notification_in.notification_type,
            is_read=False,
        )
        db.add(db_notif)
        await db.commit()
        await db.refresh(db_notif)
        return db_notif

    async def get_by_id(self, db: AsyncSession, notif_id: UUID) -> Notification | None:
        """Fetch a specific Notification by ID."""
        stmt = select(Notification).where(Notification.id == notif_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Notification]:
        """List notifications for a specific user, ordered by creation descending."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def mark_as_read(
        self, db: AsyncSession, notif_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Mark a single notification as read."""
        stmt = select(Notification).where(
            Notification.id == notif_id, Notification.user_id == user_id
        )
        result = await db.execute(stmt)
        db_notif = result.scalars().first()
        if db_notif:
            db_notif.is_read = True
            db_notif.read_at = datetime.now(UTC)
            db.add(db_notif)
            await db.commit()
            await db.refresh(db_notif)
        return db_notif

    async def mark_all_as_read(self, db: AsyncSession, user_id: UUID) -> None:
        """Mark all unread notifications for a user as read."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await db.execute(stmt)
        await db.commit()


notification_repo = NotificationRepository()
