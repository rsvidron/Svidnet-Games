"""
Shared database configuration
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database setup - use PostgreSQL from Railway if available, fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway PostgreSQL (or other PostgreSQL)
    # Handle postgres:// vs postgresql:// URL scheme
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
    print(f"✓ Using PostgreSQL database")
else:
    # Local SQLite fallback
    DATABASE_URL = "sqlite:///./oauth_gamedb.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"⚠ Using SQLite database (data will not persist on Railway)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
