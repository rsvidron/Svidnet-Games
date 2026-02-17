"""
Trivia game schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TriviaQuestion(BaseModel):
    """A single trivia question"""
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_answer: int = Field(..., ge=0, le=3)
    explanation: str
    category: str


class StartGameRequest(BaseModel):
    """Request to start a new trivia game"""
    category: str = Field(default="general", description="Question category")
    difficulty: str = Field(default="5th_grade", description="Difficulty level")
    num_questions: int = Field(default=10, ge=5, le=20, description="Number of questions")


class StartGameResponse(BaseModel):
    """Response when starting a game"""
    game_id: int
    category: str
    difficulty: str
    total_questions: int
    first_question: dict
    current_index: int
    message: str


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer"""
    selected_answer: int = Field(..., ge=0, le=3, description="Index of selected option (0-3)")
    time_taken_seconds: Optional[int] = Field(None, ge=0, description="Time taken to answer")


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer"""
    is_correct: bool
    correct_answer: int
    explanation: str
    current_score: int
    correct_count: int
    wrong_count: int
    next_question: Optional[dict] = None
    game_completed: bool
    final_stats: Optional[dict] = None


class GameStats(BaseModel):
    """Statistics for a completed game"""
    game_id: int
    score: int
    correct_answers: int
    wrong_answers: int
    total_questions: int
    accuracy: int  # Percentage
    time_taken_seconds: Optional[int]
    category: str


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry"""
    rank: int
    user_id: int
    username: str
    best_score: int
    best_accuracy: int
    total_games: int
    fastest_time: Optional[int]


class LeaderboardResponse(BaseModel):
    """Leaderboard response"""
    category: str
    entries: List[LeaderboardEntry]
    user_rank: Optional[int] = None
    total_players: int
