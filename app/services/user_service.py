"""User management business logic service."""

from typing import Any

from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate


class UserService:
    """Service class for user-related business operations."""

    def register_user(self, user_in: UserCreate) -> dict[str, Any]:
        """Register a new user in the system after validating email uniqueness.

        Args:
            user_in: The user registration input schema.

        Returns:
            dict[str, Any]: The created user record dictionary.

        Raises:
            HTTPException: If the email is already registered.
        """
        existing_user = user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email is already registered.",
            )

        hashed = hash_password(user_in.password)
        return user_repo.create(user_in, hashed)

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate user credentials.

        Args:
            email: User email.
            password: User plain-text password.

        Returns:
            dict[str, Any] | None: User record dictionary if authenticated,
                None otherwise.
        """
        user = user_repo.get_by_email(email)
        if not user:
            return None

        if not verify_password(password, user["hashed_password"]):
            return None

        return user


user_service = UserService()
