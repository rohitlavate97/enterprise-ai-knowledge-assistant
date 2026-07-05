"""Department model for relational database."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.user import User


class Department(Base, AuditMixin):
    """Department representation in the relational database."""

    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    teams: Mapped[list["Team"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="department")
