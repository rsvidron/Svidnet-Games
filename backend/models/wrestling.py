"""
Wrestling Predictions Models

Events → Questions → Submissions → Answers
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Float
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class WrestlingEvent(Base):
    """A wrestling show (e.g. Royal Rumble 2025)"""
    __tablename__ = "wrestling_events"

    id            = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=True)
    image_url     = Column(String(500), nullable=True)   # poster / banner
    event_date    = Column(DateTime(timezone=True), nullable=True)
    is_locked     = Column(Boolean, default=False, nullable=False)  # locks submissions
    is_graded     = Column(Boolean, default=False, nullable=False)  # answers submitted
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    questions     = relationship("WrestlingQuestion", back_populates="event",
                                 cascade="all, delete-orphan", order_by="WrestlingQuestion.sort_order")
    submissions   = relationship("WrestlingSubmission", back_populates="event",
                                 cascade="all, delete-orphan")


class WrestlingQuestion(Base):
    """A question on a wrestling prediction form"""
    __tablename__ = "wrestling_questions"

    id               = Column(Integer, primary_key=True, index=True)
    event_id         = Column(Integer, ForeignKey("wrestling_events.id"), nullable=False, index=True)
    question_text    = Column(Text, nullable=False)
    question_type    = Column(String(20), nullable=False)   # short_answer | multiple_choice | dropdown | checkbox
    options          = Column(JSON, nullable=True)           # list of strings for mc/dropdown/checkbox
    correct_answer   = Column(JSON, nullable=True)           # string (short/mc/dropdown) or list (checkbox)
    counts_for_score = Column(Boolean, default=True, nullable=False)
    sort_order       = Column(Integer, default=0, nullable=False)

    event            = relationship("WrestlingEvent", back_populates="questions")
    answers          = relationship("WrestlingAnswer", back_populates="question",
                                    cascade="all, delete-orphan")


class WrestlingSubmission(Base):
    """One user's full submission for an event"""
    __tablename__ = "wrestling_submissions"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_submission_event_user"),)

    id         = Column(Integer, primary_key=True, index=True)
    event_id   = Column(Integer, ForeignKey("wrestling_events.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    score      = Column(Float, nullable=True)     # filled in after grading
    max_score  = Column(Float, nullable=True)     # total scoreable questions

    event      = relationship("WrestlingEvent", back_populates="submissions")
    answers    = relationship("WrestlingAnswer", back_populates="submission",
                              cascade="all, delete-orphan")


class WrestlingAnswer(Base):
    """One answer within a submission"""
    __tablename__ = "wrestling_answers"
    __table_args__ = (UniqueConstraint("submission_id", "question_id", name="uq_answer_sub_q"),)

    id            = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("wrestling_submissions.id"), nullable=False, index=True)
    question_id   = Column(Integer, ForeignKey("wrestling_questions.id"), nullable=False, index=True)
    answer_value  = Column(JSON, nullable=True)    # string or list
    is_correct    = Column(Boolean, nullable=True) # null until graded
    points_earned = Column(Float, nullable=True)   # null until graded (supports partial)

    submission    = relationship("WrestlingSubmission", back_populates="answers")
    question      = relationship("WrestlingQuestion", back_populates="answers")
