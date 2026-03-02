"""
Admin endpoints for platform management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional

from ...db.session import get_async_db
from ...models.user import User
from ...models.page_access import PageAccess
from ...api.deps import get_current_user

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class PageAccessBase(BaseModel):
    page_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    allowed_roles: List[str] = Field(..., min_items=1)
    description: Optional[str] = None
    is_active: bool = True


class PageAccessCreate(PageAccessBase):
    pass


class PageAccessUpdate(BaseModel):
    display_name: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PageAccessResponse(PageAccessBase):
    id: int

    class Config:
        from_attributes = True


class CheckAccessRequest(BaseModel):
    page_name: str


class CheckAccessResponse(BaseModel):
    has_access: bool
    page_name: str
    user_role: str
    message: str


# ============================================
# HELPER FUNCTIONS
# ============================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================
# PAGE ACCESS ENDPOINTS
# ============================================

@router.get("/page-access", response_model=List[PageAccessResponse])
async def get_all_page_access(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all page access configurations (Admin only)
    """
    result = await db.execute(
        select(PageAccess).order_by(PageAccess.page_name)
    )
    pages = result.scalars().all()
    return pages


@router.get("/page-access/{page_name}", response_model=PageAccessResponse)
async def get_page_access(
    page_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin)
):
    """
    Get page access configuration by page name (Admin only)
    """
    result = await db.execute(
        select(PageAccess).where(PageAccess.page_name == page_name)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page access configuration for '{page_name}' not found"
        )

    return page


@router.post("/page-access", response_model=PageAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_page_access(
    page_data: PageAccessCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new page access configuration (Admin only)
    """
    # Check if page already exists
    result = await db.execute(
        select(PageAccess).where(PageAccess.page_name == page_data.page_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page access configuration for '{page_data.page_name}' already exists"
        )

    # Validate roles
    valid_roles = {"basic", "user", "admin"}
    invalid_roles = set(page_data.allowed_roles) - valid_roles
    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles: {', '.join(invalid_roles)}. Valid roles are: basic, user, admin"
        )

    # Create new page access
    new_page = PageAccess(
        page_name=page_data.page_name,
        display_name=page_data.display_name,
        allowed_roles=page_data.allowed_roles,
        description=page_data.description,
        is_active=page_data.is_active
    )

    db.add(new_page)
    await db.commit()
    await db.refresh(new_page)

    return new_page


@router.put("/page-access/{page_name}", response_model=PageAccessResponse)
async def update_page_access(
    page_name: str,
    page_data: PageAccessUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin)
):
    """
    Update page access configuration (Admin only)
    """
    # Get existing page
    result = await db.execute(
        select(PageAccess).where(PageAccess.page_name == page_name)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page access configuration for '{page_name}' not found"
        )

    # Validate roles if provided
    if page_data.allowed_roles is not None:
        valid_roles = {"basic", "user", "admin"}
        invalid_roles = set(page_data.allowed_roles) - valid_roles
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {', '.join(invalid_roles)}. Valid roles are: basic, user, admin"
            )
        page.allowed_roles = page_data.allowed_roles

    # Update fields
    if page_data.display_name is not None:
        page.display_name = page_data.display_name
    if page_data.description is not None:
        page.description = page_data.description
    if page_data.is_active is not None:
        page.is_active = page_data.is_active

    await db.commit()
    await db.refresh(page)

    return page


@router.delete("/page-access/{page_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page_access(
    page_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete page access configuration (Admin only)
    """
    result = await db.execute(
        select(PageAccess).where(PageAccess.page_name == page_name)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page access configuration for '{page_name}' not found"
        )

    await db.delete(page)
    await db.commit()


@router.post("/page-access/check", response_model=CheckAccessResponse)
async def check_page_access(
    request: CheckAccessRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if current user has access to a specific page
    """
    result = await db.execute(
        select(PageAccess).where(PageAccess.page_name == request.page_name)
    )
    page = result.scalar_one_or_none()

    # If page access is not configured, allow access by default (backward compatibility)
    if not page:
        return CheckAccessResponse(
            has_access=True,
            page_name=request.page_name,
            user_role=current_user.role,
            message="Page access not configured, allowing access"
        )

    # Check if page is active
    if not page.is_active:
        return CheckAccessResponse(
            has_access=False,
            page_name=request.page_name,
            user_role=current_user.role,
            message="This page is currently disabled"
        )

    # Check if user's role is in allowed roles
    has_access = current_user.role in page.allowed_roles

    return CheckAccessResponse(
        has_access=has_access,
        page_name=request.page_name,
        user_role=current_user.role,
        message="Access granted" if has_access else f"Access denied. Required roles: {', '.join(page.allowed_roles)}"
    )


@router.get("/available-roles")
async def get_available_roles(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available user roles
    """
    return {
        "roles": [
            {"value": "basic", "label": "Basic", "description": "Basic access level"},
            {"value": "user", "label": "User", "description": "Standard user access"},
            {"value": "admin", "label": "Admin", "description": "Full administrative access"}
        ]
    }
