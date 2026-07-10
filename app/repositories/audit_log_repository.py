"""AuditLog repository layer for tracking administrative events."""

import logging
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditLogRepository:
    """Repository class managing audit log writes and queries."""

    async def log(
        self,
        db: AsyncSession,
        action: str,
        details: str,
        user_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Create a new AuditLog entry.

        This method catches all exceptions internally to prevent auditing failures from
        disrupting primary database transaction scopes.
        """
        try:
            db_log = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                payload=payload,
            )
            db.add(db_log)
            await db.commit()
            return db_log
        except Exception as err:
            logger.error("Audit log write failed for action %s: %s", action, str(err))
            return None

    async def list_logs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        action_filter: str | None = None,
        user_filter: UUID | None = None,
    ) -> Sequence[AuditLog]:
        """Fetch audit logs with optional pagination and filtering."""
        stmt = select(AuditLog)
        if action_filter:
            stmt = stmt.where(AuditLog.action == action_filter)
        if user_filter:
            stmt = stmt.where(AuditLog.user_id == user_filter)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()


audit_log_repo = AuditLogRepository()
