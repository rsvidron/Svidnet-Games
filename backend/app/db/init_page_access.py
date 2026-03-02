"""
Initialize page access control data
Run this on startup to seed default page access configurations
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.page_access import PageAccess


async def init_page_access(db: AsyncSession):
    """Initialize page access configurations with defaults"""

    # Check if page access data already exists
    result = await db.execute(select(PageAccess))
    if result.first() is not None:
        # Data already exists, skip initialization
        return

    # Default page access configurations
    default_pages = [
        PageAccess(
            page_name="sportsbook",
            display_name="Sportsbook",
            allowed_roles=["admin"],
            description="Sports betting and predictions page",
            is_active=True
        ),
        PageAccess(
            page_name="wordle",
            display_name="Wordle",
            allowed_roles=["basic", "user", "admin"],
            description="Daily and endless Wordle games",
            is_active=True
        ),
        PageAccess(
            page_name="wrestling",
            display_name="Wrestling",
            allowed_roles=["user", "admin"],
            description="Wrestling-themed games and content",
            is_active=True
        ),
        PageAccess(
            page_name="trivia-game",
            display_name="Trivia Game",
            allowed_roles=["basic", "user", "admin"],
            description="Trivia game modes",
            is_active=True
        ),
        PageAccess(
            page_name="movies",
            display_name="Movies",
            allowed_roles=["basic", "user", "admin"],
            description="Movie-related games and leaderboards",
            is_active=True
        ),
        PageAccess(
            page_name="dashboard",
            display_name="Dashboard",
            allowed_roles=["basic", "user", "admin"],
            description="User dashboard",
            is_active=True
        ),
        PageAccess(
            page_name="profile",
            display_name="Profile",
            allowed_roles=["basic", "user", "admin"],
            description="User profile page",
            is_active=True
        ),
        PageAccess(
            page_name="rankings",
            display_name="Rankings",
            allowed_roles=["basic", "user", "admin"],
            description="Global rankings and leaderboards",
            is_active=True
        ),
        PageAccess(
            page_name="admin",
            display_name="Admin Panel",
            allowed_roles=["admin"],
            description="Admin panel for managing the platform",
            is_active=True
        )
    ]

    # Add all default pages
    for page in default_pages:
        db.add(page)

    await db.commit()

    return len(default_pages)
