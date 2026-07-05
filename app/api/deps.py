"""FastAPI dependency injection utilities."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_token
from app.repositories.user_repository import user_repo
from app.schemas.user import UserRole

# Define the OAuth2 password bearer flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, Any]:
    """Retrieve and validate the current authenticated user from JWT token.

    Args:
        token: Cryptographically signed JWT token from Authorization header.

    Returns:
        dict[str, Any]: The authenticated user's dictionary.

    Raises:
        HTTPException: If token is invalid, expired, or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        try:
            user_id = UUID(user_id_str)
        except ValueError as err:
            raise credentials_exception from err
    except JWTError as err:
        raise credentials_exception from err

    user = user_repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Ensure the authenticated user is currently active.

    Args:
        current_user: The authenticated user dictionary.

    Returns:
        dict[str, Any]: The active user dictionary.

    Raises:
        HTTPException: If the user is inactive.
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency for checking Role-Based Access Control permissions on endpoints."""

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        """Initialize the role checker with allowed roles.

        Args:
            allowed_roles: A list of UserRole enums allowed to access the endpoint.
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self, current_user: Annotated[dict[str, Any], Depends(get_current_active_user)]
    ) -> dict[str, Any]:
        """Evaluate if the current active user possesses an authorized role.

        Args:
            current_user: The current active user.

        Returns:
            dict[str, Any]: The authorized user.

        Raises:
            HTTPException: 403 Forbidden error if user is not authorized.
        """
        user_role = current_user.get("role")
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user
