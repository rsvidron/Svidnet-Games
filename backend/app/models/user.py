"""
User and UserProfile models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from ..db.base import Base, TimestampMixin, IdMixin


class User(Base, IdMixin, TimestampMixin):
    """User model for authentication and basic info"""

    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="basic", nullable=False, index=True)  # basic | user | admin
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")
    friendships = relationship("Friendship", foreign_keys="Friendship.user_id", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class UserProfile(Base, IdMixin, TimestampMixin):
    """User profile with stats and achievements"""

    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    bio = Column(String, nullable=True)
    elo_rating = Column(Integer, default=1200, nullable=False, index=True)
    trivia_accuracy_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    wordle_current_streak = Column(Integer, default=0, nullable=False)
    wordle_max_streak = Column(Integer, default=0, nullable=False)
    total_games_played = Column(Integer, default=0, nullable=False)
    total_wins = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, elo={self.elo_rating})>"


class Friendship(Base, IdMixin, TimestampMixin):
    """Friendship/friend requests between users"""

    __tablename__ = "friendships"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, accepted, blocked

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])

    def __repr__(self):
        return f"<Friendship(user_id={self.user_id}, friend_id={self.friend_id}, status='{self.status}')>"


class Notification(Base, IdMixin, TimestampMixin):
    """User notifications"""

    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    action_url = Column(String(500), nullable=True)
    extra_data = Column(String, nullable=True)  # JSON string (renamed from metadata to avoid SQLAlchemy conflict)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}')>"
