"""
Admin models for custom trivia categories and questions
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base


class TriviaCategory(Base):
    """Custom trivia category"""
    __tablename__ = "trivia_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Emoji or icon name
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CustomTriviaQuestion(Base):
    """Custom trivia question created by admin"""
    __tablename__ = "custom_trivia_questions"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("trivia_categories.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    option_a = Column(String(500), nullable=False)
    option_b = Column(String(500), nullable=False)
    option_c = Column(String(500), nullable=False)
    option_d = Column(String(500), nullable=False)
    correct_answer = Column(Integer, nullable=False)  # 0-3 for A-D
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default="medium", nullable=False)  # easy, medium, hard
    is_active = Column(Boolean, default=True, nullable=False)
    times_used = Column(Integer, default=0, nullable=False)
    times_correct = Column(Integer, default=0, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class WordleWord(Base):
    """Custom Wordle word managed by admin"""
    __tablename__ = "wordle_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(5), unique=True, nullable=False, index=True)  # 5-letter word
    difficulty = Column(String(20), default="medium", nullable=False)  # easy, medium, hard
    is_active = Column(Boolean, default=True, nullable=False)
    times_used = Column(Integer, default=0, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
