"""
Game-related models: GameMode, GameRoom, GameSession, GameParticipant
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from ..db.base import Base, TimestampMixin, IdMixin


class GameMode(Base, IdMixin, TimestampMixin):
    """Available game modes"""

    __tablename__ = "game_modes"

    mode_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    min_players = Column(Integer, default=1, nullable=False)
    max_players = Column(Integer, default=1, nullable=False)
    is_multiplayer = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    game_rooms = relationship("GameRoom", back_populates="game_mode")
    game_sessions = relationship("GameSession", back_populates="game_mode")

    def __repr__(self):
        return f"<GameMode(id={self.id}, name='{self.mode_name}')>"


class GameRoom(Base, IdMixin, TimestampMixin):
    """Multiplayer game rooms"""

    __tablename__ = "game_rooms"

    room_code = Column(String(6), unique=True, nullable=False, index=True)
    game_mode_id = Column(Integer, ForeignKey("game_modes.id", ondelete="RESTRICT"), nullable=False)
    host_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_name = Column(String(100), nullable=True)
    max_players = Column(Integer, default=8, nullable=False)
    current_players = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="waiting", nullable=False, index=True)  # waiting, in_progress, completed, cancelled
    settings = Column(String, nullable=True)  # JSON string for game settings
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    game_mode = relationship("GameMode", back_populates="game_rooms")
    host = relationship("User", foreign_keys=[host_user_id])
    participants = relationship("GameParticipant", back_populates="room", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="room")

    def __repr__(self):
        return f"<GameRoom(id={self.id}, code='{self.room_code}', status='{self.status}')>"


class GameParticipant(Base, IdMixin, TimestampMixin):
    """Players in a game room"""

    __tablename__ = "game_participants"

    room_id = Column(Integer, ForeignKey("game_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), default="player", nullable=False)  # player, spectator
    score = Column(Integer, default=0, nullable=False)
    position = Column(Integer, nullable=True)
    is_ready = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    room = relationship("GameRoom", back_populates="participants")
    user = relationship("User")

    def __repr__(self):
        return f"<GameParticipant(room_id={self.room_id}, user_id={self.user_id}, role='{self.role}')>"


class GameSession(Base, IdMixin, TimestampMixin):
    """Individual game sessions (single player or multiplayer)"""

    __tablename__ = "game_sessions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_mode_id = Column(Integer, ForeignKey("game_modes.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("game_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    score = Column(Integer, default=0, nullable=False)
    accuracy_percentage = Column(Numeric(5, 2), nullable=True)
    questions_answered = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    elo_change = Column(Integer, default=0, nullable=False)
    position = Column(Integer, nullable=True)
    game_data = Column(String, nullable=True)  # JSON string for game-specific data
    completed = Column(Boolean, default=False, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    game_mode = relationship("GameMode", back_populates="game_sessions")
    room = relationship("GameRoom", back_populates="game_sessions")
    user_answers = relationship("UserAnswer", back_populates="game_session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameSession(id={self.id}, user_id={self.user_id}, mode_id={self.game_mode_id}, score={self.score})>"
