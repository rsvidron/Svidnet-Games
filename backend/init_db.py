"""
Database initialization script
Create tables and seed initial data
"""
from sqlalchemy import text, select
from database import Base, engine, SessionLocal

# Import all models so they're registered with Base
from app.models.user import User, UserProfile, Friendship, Notification
from app.models.trivia import Category, TriviaQuestion, TriviaAnswer
from app.models.game import GameMode, GameRoom, GameParticipant, GameSession
from app.models.page_access import PageAccess


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def seed_page_access():
    """Seed default page access configurations"""
    print("Seeding page access data...")

    db = SessionLocal()
    try:
        # Check if data already exists
        result = db.execute(select(PageAccess)).first()
        if result is not None:
            print("Page access data already exists, skipping seed")
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

        db.commit()
        print(f"✅ Seeded {len(default_pages)} page access configurations")

    except Exception as e:
        print(f"⚠️  Failed to seed page access data: {e}")
        db.rollback()
    finally:
        db.close()


def update_user_role_constraint():
    """Update users table to support basic, user, admin roles"""
    print("Updating user role constraint...")
    db = SessionLocal()
    try:
        # Drop old constraint if exists
        db.execute(text("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
        """))

        # Add new constraint
        db.execute(text("""
            ALTER TABLE users ADD CONSTRAINT users_role_check
            CHECK (role IN ('basic', 'user', 'admin'));
        """))

        db.commit()
        print("✅ User role constraint updated")
    except Exception as e:
        print(f"⚠️  Failed to update constraint (may already exist): {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)

    create_tables()
    update_user_role_constraint()
    seed_page_access()

    print("=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
