"""Authentication API endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_active_user
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.repositories.user_repository import user_repo
from app.schemas.auth import Token, TokenRefreshRequest
from app.schemas.user import UserCreate, UserResponse, UserRole
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_in: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Register a new user in the system."""
    return await user_service.register_user(db, user_in)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """OAuth2 compatible token login, returning access and refresh tokens.

    Validates credentials against email and password.
    """
    user = await user_service.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    subject = {"sub": str(user.id), "role": user.role}
    return {
        "access_token": create_access_token(subject=subject),
        "refresh_token": create_refresh_token(subject=subject),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_in: TokenRefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Generate new access and refresh tokens using a valid refresh token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = decode_token(refresh_in.refresh_token)
        if payload.get("typ") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as err:
        raise credentials_exception from err

    user = await user_repo.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    subject = {"sub": str(user.id), "role": user.role}
    return {
        "access_token": create_access_token(subject=subject),
        "refresh_token": create_refresh_token(subject=subject),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """Get profile details of the current logged-in user."""
    return current_user


@router.get("/admin-only")
async def admin_only_endpoint(
    current_user: Annotated[User, Depends(RoleChecker([UserRole.ADMIN]))],
) -> Any:
    """An admin-only endpoint to verify role checking dependencies."""
    return {"message": f"Hello Admin {current_user.full_name}"}
