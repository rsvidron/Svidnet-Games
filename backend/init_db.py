"""
Database initialization script
Create tables and seed initial data
"""
import asyncio
from sqlalchemy import text
from app.db.session import async_engine, get_async_db
from app.db.base import Base

# Import all models so they're registered with Base
from app.models.user import User, UserProfile, Friendship, Notification
from app.models.trivia import Category, TriviaQuestion, TriviaAnswer
from app.models.game import GameMode, GameRoom, GameParticipant, GameSession
from app.models.page_access import PageAccess


async def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    async with async_engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")


async def seed_page_access():
    """Seed default page access configurations"""
    print("Seeding page access data...")

    async for db in get_async_db():
        try:
            # Check if data already exists
            from sqlalchemy import select
            result = await db.execute(select(PageAccess))
            if result.first() is not None:
                print("Page access data already exists, skipping seed")
                break

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
            print(f"✅ Seeded {len(default_pages)} page access configurations")

        except Exception as e:
            print(f"⚠️  Failed to seed page access data: {e}")
            await db.rollback()

        break  # Only use first db session


async def update_user_role_constraint():
    """Update users table to support basic, user, admin roles"""
    print("Updating user role constraint...")
    async for db in get_async_db():
        try:
            # Drop old constraint if exists
            await db.execute(text("""
                ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
            """))

            # Add new constraint
            await db.execute(text("""
                ALTER TABLE users ADD CONSTRAINT users_role_check
                CHECK (role IN ('basic', 'user', 'admin'));
            """))

            await db.commit()
            print("✅ User role constraint updated")
        except Exception as e:
            print(f"⚠️  Failed to update constraint (may already exist): {e}")
            await db.rollback()

        break


async def main():
    """Main initialization function"""
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)

    await create_tables()
    await update_user_role_constraint()
    await seed_page_access()

    print("=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
