"""
User models - extracted from oauth_server for reusability
"""
from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), default="basic", nullable=False)  # basic | user | admin
    is_active = Column(Boolean, default=True, nullable=False)
    auth_provider = Column(String(20), default="local", nullable=False)  # local, google


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    elo_rating = Column(Integer, default=1200, nullable=False)
    total_games_played = Column(Integer, default=0, nullable=False)
