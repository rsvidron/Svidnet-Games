from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from datetime import datetime, timezone
from database import Base

class WordleGame(Base):
    """Wordle game session"""
    __tablename__ = "wordle_games"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_word = Column(String(5), nullable=False)  # The word to guess
    guesses = Column(JSON, nullable=False, default=list)  # List of guess attempts
    is_won = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    attempts_used = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=6, nullable=False)
    time_started = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    time_completed = Column(DateTime, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class WordleStats(Base):
    """Wordle statistics per user"""
    __tablename__ = "wordle_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    games_played = Column(Integer, default=0, nullable=False)
    games_won = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)
    guess_distribution = Column(JSON, nullable=False, default=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0})  # How many guesses to win
    last_played = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
