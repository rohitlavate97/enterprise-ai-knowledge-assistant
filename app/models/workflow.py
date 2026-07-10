"""Workflow and WorkflowTask database models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Workflow(Base, AuditMixin):
    """Represents a multi-step workflow execution graph."""

    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship()
    tasks: Mapped[list["WorkflowTask"]] = relationship(
        "WorkflowTask",
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WorkflowTask(Base, TimestampMixin):
    """Represents an individual task step in a workflow execution graph."""

    __tablename__ = "workflow_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "research", "document", etc.
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_delay: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False
    )  # seconds

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    depends_on_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflow_tasks.id", ondelete="SET NULL"), nullable=True
    )

    conditional_routes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="tasks")
    depends_on: Mapped["WorkflowTask | None"] = relationship(
        remote_side=[id], post_update=True  # noqa: A003
    )
