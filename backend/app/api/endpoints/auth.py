"""
Authentication endpoints: register, login, refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import timedelta

from ...db.session import get_async_db
from ...core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from ...core.config import settings
from ...models.user import User, UserProfile

router = APIRouter()


# Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    is_verified: bool

    class Config:
        from_attributes = True


class TokenRefresh(BaseModel):
    refresh_token: str


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register a new user

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        JWT tokens

    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role="user"
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create user profile (should be handled by trigger, but doing it manually here)
    user_profile = UserProfile(
        user_id=new_user.id,
        elo_rating=settings.DEFAULT_ELO_RATING
    )
    db.add(user_profile)
    await db.commit()

    # Create tokens
    access_token = create_access_token(
        data={"sub": new_user.id, "username": new_user.username, "role": new_user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": new_user.id}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Login user and return JWT tokens

    Args:
        credentials: Username and password
        db: Database session

    Returns:
        JWT tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user by username
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Refresh access token using refresh token

    Args:
        token_data: Refresh token
        db: Database session

    Returns:
        New JWT tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return current_user


# Import dependency
from ...api.deps import get_current_user
