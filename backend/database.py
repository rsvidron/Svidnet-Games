"""
Shared database configuration
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database setup - use PostgreSQL from Railway if available, fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL not set, try building from individual Railway PostgreSQL variables
if not DATABASE_URL:
    pghost = os.getenv("PGHOST")
    pgport = os.getenv("PGPORT", "5432")
    pguser = os.getenv("PGUSER", "postgres")
    pgpassword = os.getenv("PGPASSWORD")
    pgdatabase = os.getenv("PGDATABASE", "railway")

    if pghost and pgpassword:
        # Use pg8000 driver (pure Python, no system dependencies)
        DATABASE_URL = f"postgresql+pg8000://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"

if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    # PostgreSQL connection
    # Handle postgres:// vs postgresql:// URL scheme
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # If using psycopg2 dialect, switch to pg8000 (pure Python)
    if "postgresql://" in DATABASE_URL and "+pg8000" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
    print(f"✓ Using PostgreSQL database with pg8000 driver")
else:
    # Local SQLite fallback
    DATABASE_URL = "sqlite:///./oauth_gamedb.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"⚠ Using SQLite database (data will not persist on Railway)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
