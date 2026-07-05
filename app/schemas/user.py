"""Pydantic schemas for User models and Role-Based Access Control."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    """Roles for Role-Based Access Control."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class UserBase(BaseModel):
    """Shared properties for User schemas."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """Properties to receive on User registration."""

    password: str = Field(min_length=8, max_length=72)


class UserUpdate(BaseModel):
    """Properties to receive on User profile update."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Properties to return to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
