"""In-memory User Repository for authentication before Database Milestone."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.schemas.user import UserCreate


class UserRepository:
    """Mock in-memory user repository simulating database access."""

    # Class-level storage for mock users
    _users: dict[UUID, dict[str, Any]] = {}

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Retrieve a user by their email address.

        Args:
            email: User email.

        Returns:
            dict[str, Any] | None: User record dictionary or None if not found.
        """
        for user in self._users.values():
            if user["email"].lower() == email.lower():
                return user
        return None

    def get_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        """Retrieve a user by their unique UUID.

        Args:
            user_id: User UUID.

        Returns:
            dict[str, Any] | None: User record dictionary or None if not found.
        """
        return self._users.get(user_id)

    def create(self, user_in: UserCreate, hashed_password: str) -> dict[str, Any]:
        """Simulate creating a user in the database.

        Args:
            user_in: The user registration schema.
            hashed_password: The pre-hashed password.

        Returns:
            dict[str, Any]: The created user record dictionary.
        """
        now = datetime.now(UTC)
        user_id = uuid4()
        user_record = {
            "id": user_id,
            "email": user_in.email,
            "hashed_password": hashed_password,
            "full_name": user_in.full_name,
            "is_active": user_in.is_active,
            "role": user_in.role,
            "created_at": now,
            "updated_at": now,
        }
        self._users[user_id] = user_record
        return user_record

    def clear(self) -> None:
        """Clear all mock users. Handy for testing."""
        self._users.clear()


user_repo = UserRepository()
