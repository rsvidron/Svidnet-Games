"""
Trivia-related models: Category, TriviaQuestion, TriviaAnswer, UserAnswer
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from ..db.base import Base, TimestampMixin, IdMixin


class Category(Base, IdMixin, TimestampMixin):
    """Trivia categories"""

    __tablename__ = "categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True)
    difficulty_level = Column(String(20), nullable=True, index=True)  # easy, medium, hard, expert
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    trivia_questions = relationship("TriviaQuestion", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class TriviaQuestion(Base, IdMixin, TimestampMixin):
    """Trivia questions"""

    __tablename__ = "trivia_questions"

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    question_text = Column(Text, nullable=False)
    difficulty = Column(String(20), nullable=True, index=True)  # easy, medium, hard, expert
    question_type = Column(String(50), default="multiple_choice", nullable=False)  # multiple_choice, true_false, fill_blank
    points = Column(Integer, default=100, nullable=False)
    time_limit_seconds = Column(Integer, default=30, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False, index=True)
    source = Column(String(50), default="manual", nullable=False, index=True)  # manual, ai_generated, imported
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    category = relationship("Category", back_populates="trivia_questions")
    answers = relationship("TriviaAnswer", back_populates="question", cascade="all, delete-orphan")
    user_answers = relationship("UserAnswer", back_populates="question")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<TriviaQuestion(id={self.id}, difficulty='{self.difficulty}', approved={self.is_approved})>"


class TriviaAnswer(Base, IdMixin, TimestampMixin):
    """Answer options for trivia questions"""

    __tablename__ = "trivia_answers"

    question_id = Column(Integer, ForeignKey("trivia_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    question = relationship("TriviaQuestion", back_populates="answers")

    def __repr__(self):
        return f"<TriviaAnswer(id={self.id}, question_id={self.question_id}, correct={self.is_correct})>"


class UserAnswer(Base, IdMixin):
    """Track user answers to trivia questions"""

    __tablename__ = "user_answers"

    game_session_id = Column(Integer, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("trivia_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_id = Column(Integer, ForeignKey("trivia_answers.id", ondelete="SET NULL"), nullable=True)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    points_earned = Column(Integer, default=0, nullable=False)
    answered_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    game_session = relationship("GameSession", back_populates="user_answers")
    question = relationship("TriviaQuestion", back_populates="user_answers")
    user = relationship("User")
    answer = relationship("TriviaAnswer")

    def __repr__(self):
        return f"<UserAnswer(id={self.id}, user_id={self.user_id}, correct={self.is_correct})>"


class AIGeneratedQuestion(Base, IdMixin, TimestampMixin):
    """AI-generated questions pending approval"""

    __tablename__ = "ai_generated_questions"

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    question_data = Column(String, nullable=False)  # JSON string with full question + answers
    generation_prompt = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    category = relationship("Category")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<AIGeneratedQuestion(id={self.id}, status='{self.status}')>"
