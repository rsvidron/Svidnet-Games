"""
Create database tables for SQLite
"""
from app.db.base import Base
from app.db.session_sqlite import engine
from app.models.user import User, UserProfile, Friendship, Notification
from app.models.game import GameMode, GameRoom, GameParticipant, GameSession
from app.models.trivia import Category, TriviaQuestion, TriviaAnswer, UserAnswer, AIGeneratedQuestion

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ All tables created successfully!")

# Create sample game modes
from app.db.session_sqlite import SessionLocal

db = SessionLocal()

# Check if game modes exist
from sqlalchemy import select
result = db.execute(select(GameMode)).first()

if not result:
    print("Seeding game modes...")
    game_modes = [
        GameMode(
            mode_name="fifth_grade",
            display_name="5th Grade Trivia",
            description="Progressive difficulty trivia challenge",
            min_players=1,
            max_players=1,
            is_multiplayer=False
        ),
        GameMode(
            mode_name="jeopardy",
            display_name="Jeopardy Mode",
            description="Category-based trivia with buzzer system",
            min_players=1,
            max_players=8,
            is_multiplayer=True
        ),
        GameMode(
            mode_name="multiplayer_trivia",
            display_name="Multiplayer Trivia",
            description="Real-time trivia competition",
            min_players=2,
            max_players=8,
            is_multiplayer=True
        ),
        GameMode(
            mode_name="daily_wordle",
            display_name="Daily Wordle",
            description="One puzzle per day shared globally",
            min_players=1,
            max_players=1,
            is_multiplayer=False
        ),
        GameMode(
            mode_name="endless_wordle",
            display_name="Endless Wordle",
            description="Unlimited word puzzles",
            min_players=1,
            max_players=1,
            is_multiplayer=False
        )
    ]

    for mode in game_modes:
        db.add(mode)

    db.commit()
    print(f"✅ Added {len(game_modes)} game modes")

# Create sample categories
result = db.execute(select(Category)).first()

if not result:
    print("Seeding categories...")
    categories = [
        Category(name="Science", description="General science questions", difficulty_level="medium", is_active=True),
        Category(name="History", description="World history trivia", difficulty_level="medium", is_active=True),
        Category(name="Sports", description="Sports knowledge", difficulty_level="easy", is_active=True),
        Category(name="Geography", description="World geography", difficulty_level="hard", is_active=True),
        Category(name="Pop Culture", description="Movies, music, and entertainment", difficulty_level="easy", is_active=True)
    ]

    for cat in categories:
        db.add(cat)

    db.commit()
    print(f"✅ Added {len(categories)} categories")

db.close()
print("\n🎮 Database initialized and ready!")
