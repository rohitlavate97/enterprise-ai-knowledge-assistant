"""User management business logic service."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.department_repository import department_repo
from app.repositories.team_repository import team_repo
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserUpdate


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

    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> User:
        """Retrieve a user or raise 404 Not Found.

        Args:
            db: Active database async session.
            user_id: The user's UUID.

        Returns:
            User: The retrieved User model instance.

        Raises:
            HTTPException: If the user is not found.
        """
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    async def update_user(
        self, db: AsyncSession, user_id: UUID, user_in: UserUpdate
    ) -> User:
        """Update a user's details, role, department, or team.

        Args:
            db: Active database async session.
            user_id: The UUID of the user to update.
            user_in: The user update payload schema.

        Returns:
            User: The updated User model instance.

        Raises:
            HTTPException: If email exists or team/department ID is invalid.
        """
        db_user = await self.get_user_by_id(db, user_id)

        # Verify department if updated
        if user_in.department_id:
            dep = await department_repo.get_by_id(db, user_in.department_id)
            if not dep:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Department with ID '{user_in.department_id}' not found.",
                )

        # Verify team if updated
        if user_in.team_id:
            team = await team_repo.get_by_id(db, user_in.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Team with ID '{user_in.team_id}' not found.",
                )

        # Verify email uniqueness if changed
        if user_in.email and user_in.email != db_user.email:
            existing = await user_repo.get_by_email(db, user_in.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email is already registered.",
                )

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user


user_service = UserService()
