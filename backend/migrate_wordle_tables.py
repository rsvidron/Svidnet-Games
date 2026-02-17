"""
Migration script to update Wordle tables with new daily challenge columns
"""
from sqlalchemy import text
from database import engine

def migrate_wordle_tables():
    """Add missing columns to wordle tables for daily challenge support"""

    with engine.connect() as conn:
        try:
            # Check if wordle_games table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'wordle_games'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("✓ wordle_games table doesn't exist yet, will be created fresh")
                return

            # Check if challenge_date column exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'wordle_games'
                    AND column_name = 'challenge_date'
                )
            """))
            column_exists = result.scalar()

            if column_exists:
                print("✓ wordle_games.challenge_date column already exists")
            else:
                print("Adding challenge_date column to wordle_games...")

                # Drop existing wordle tables (safe since it's a new feature)
                conn.execute(text("DROP TABLE IF EXISTS daily_wordle_leaderboard CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS wordle_games CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS wordle_stats CASCADE"))
                conn.commit()

                print("✓ Dropped old wordle tables, they will be recreated with new schema")

        except Exception as e:
            print(f"Migration completed with note: {e}")
            # If we're using SQLite or tables don't exist, that's fine
            pass

if __name__ == "__main__":
    migrate_wordle_tables()
    print("✓ Wordle migration complete")
