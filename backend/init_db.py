"""
Database initialization script
Run migrations from SQL files on startup
"""
import asyncio
import os
from pathlib import Path
from sqlalchemy import text
from app.db.session import get_async_db


async def run_migrations():
    """Run SQL migrations from the migrations directory"""
    migrations_dir = Path(__file__).parent / "migrations"

    if not migrations_dir.exists():
        print("No migrations directory found, skipping...")
        return

    # Get all SQL files in migrations directory
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print("No SQL migrations found")
        return

    async for db in get_async_db():
        for sql_file in sql_files:
            try:
                print(f"Running migration: {sql_file.name}")

                with open(sql_file, 'r') as f:
                    sql = f.read()

                # Split by semicolon and execute each statement
                statements = [s.strip() for s in sql.split(';') if s.strip()]

                for statement in statements:
                    if statement:
                        await db.execute(text(statement))

                await db.commit()
                print(f"✅ Migration {sql_file.name} completed")

            except Exception as e:
                print(f"⚠️  Migration {sql_file.name} failed (may already be applied): {e}")
                await db.rollback()

        break  # Only use first db session


if __name__ == "__main__":
    print("Initializing database...")
    asyncio.run(run_migrations())
    print("Database initialization complete!")
