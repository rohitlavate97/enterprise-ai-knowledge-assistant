"""Pydantic schemas for authentication and tokens."""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Schema for returned token package."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema representing token internal content."""

    sub: str | None = None
    exp: int | None = None
    role: str | None = None
    typ: str | None = None


class LoginRequest(BaseModel):
    """Schema representing login request credentials."""

    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    """Schema representing token refresh requests."""

    refresh_token: str
