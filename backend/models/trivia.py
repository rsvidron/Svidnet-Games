"""
Trivia game models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class TriviaGame(Base):
    """A trivia game session"""
    __tablename__ = "trivia_games"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="general")
    difficulty = Column(String(20), nullable=False, default="5th_grade")
    total_questions = Column(Integer, nullable=False, default=10)
    questions_data = Column(JSON, nullable=False)  # Store the questions array as JSON
    current_question_index = Column(Integer, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    wrong_answers = Column(Integer, nullable=False, default=0)
    time_started = Column(DateTime, nullable=False, default=datetime.utcnow)
    time_completed = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, nullable=False, default=False)
    time_taken_seconds = Column(Integer, nullable=True)  # Total time taken


class TriviaAnswer(Base):
    """Individual answer in a trivia game"""
    __tablename__ = "trivia_answers"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("trivia_games.id"), nullable=False, index=True)
    question_index = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    selected_answer = Column(Integer, nullable=False)  # Index of selected option (0-3)
    correct_answer = Column(Integer, nullable=False)  # Index of correct option (0-3)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)  # Time taken for this question
    answered_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TriviaLeaderboard(Base):
    """Leaderboard entries for trivia games"""
    __tablename__ = "trivia_leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    best_score = Column(Integer, nullable=False, default=0)
    best_accuracy = Column(Integer, nullable=False, default=0)  # Percentage 0-100
    total_games_played = Column(Integer, nullable=False, default=0)
    total_questions_answered = Column(Integer, nullable=False, default=0)
    total_correct_answers = Column(Integer, nullable=False, default=0)
    fastest_game_seconds = Column(Integer, nullable=True)
    last_played = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
