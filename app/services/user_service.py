"""User management business logic service."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate


class UserService:
    """Service class for user-related business operations."""

    async def register_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Register a new user in the system after validating email uniqueness.

        Args:
            db: Active database async session.
            user_in: The user registration input schema.

        Returns:
            User: The created User database model instance.

        Raises:
            HTTPException: If the email is already registered.
        """
        existing_user = await user_repo.get_by_email(db, user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email is already registered.",
            )

        hashed = hash_password(user_in.password)
        return await user_repo.create(db, user_in, hashed)

    async def authenticate(
        self, db: AsyncSession, email: str, password: str
    ) -> User | None:
        """Authenticate user credentials.

        Args:
            db: Active database async session.
            email: User email.
            password: User plain-text password.

        Returns:
            User | None: User model instance if authenticated,
                None otherwise.
        """
        user = await user_repo.get_by_email(db, email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user


user_service = UserService()
