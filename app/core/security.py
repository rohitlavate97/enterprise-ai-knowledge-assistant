"""Security utilities for password hashing and JWT token management."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt.

    Args:
        password: The plain text password.

    Returns:
        str: The hashed password string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash.

    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a cryptographically-signed JWT access token.

    Args:
        subject: The token subject (typically user ID or user data dictionary).
        expires_delta: Optional custom expiration timedelta.

    Returns:
        str: A JWT token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {"exp": expire}
    if isinstance(subject, dict):
        to_encode.update(subject)
    else:
        to_encode["sub"] = str(subject)

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(
    subject: str | dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a cryptographically-signed JWT refresh token.

    Args:
        subject: The token subject.
        expires_delta: Optional custom expiration timedelta.

    Returns:
        str: A JWT token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: dict[str, Any] = {"exp": expire}
    if isinstance(subject, dict):
        to_encode.update(subject)
    else:
        to_encode["sub"] = str(subject)

    # Add a refresh marker to prevent refresh tokens from being used as access tokens
    to_encode["typ"] = "refresh"

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        dict[str, Any]: The decoded token payload dictionary.
    """
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    return dict(payload)
