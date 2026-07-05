"""Database Repository for User models using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    """Database repository layer for managing User records."""

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Retrieve a user by their email address.

        Args:
            db: Active database async session.
            email: User email.

        Returns:
            User | None: User model instance or None if not found.
        """
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        """Retrieve a user by their unique UUID.

        Args:
            db: Active database async session.
            user_id: User UUID.

        Returns:
            User | None: User model instance or None if not found.
        """
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, user_in: UserCreate, hashed_password: str
    ) -> User:
        """Create a user in the database.

        Args:
            db: Active database async session.
            user_in: The user registration schema.
            hashed_password: The pre-hashed password.

        Returns:
            User: The created User instance.
        """
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=user_in.is_active,
            role=user_in.role,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user


user_repo = UserRepository()
