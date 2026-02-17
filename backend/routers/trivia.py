"""
Trivia game API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.trivia import TriviaGame, TriviaAnswer, TriviaLeaderboard
from schemas.trivia import (
    StartGameRequest, StartGameResponse,
    SubmitAnswerRequest, SubmitAnswerResponse,
    GameStats, LeaderboardResponse, LeaderboardEntry
)
from services.gemini_service import gemini_service

router = APIRouter(prefix="/api/trivia", tags=["trivia"])


def get_current_user_id(authorization: Optional[str] = None) -> int:
    """
    Extract user ID from authorization header
    For now, returns a mock user ID. In production, decode JWT token.
    """
    # TODO: Implement proper JWT token validation
    # For now, return user ID 1 for testing
    return 1


def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/start", response_model=StartGameResponse)
def start_game(
    request: StartGameRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Start a new trivia game

    Generates questions using Gemini AI and creates a new game session.
    """
    # Generate questions using Gemini
    questions = gemini_service.generate_trivia_questions(
        category=request.category,
        difficulty=request.difficulty,
        count=request.num_questions
    )

    if not questions:
        raise HTTPException(500, "Failed to generate trivia questions")

    # Create new game
    game = TriviaGame(
        user_id=user_id,
        category=request.category,
        difficulty=request.difficulty,
        total_questions=len(questions),
        questions_data=questions,
        current_question_index=0,
        score=0,
        correct_answers=0,
        wrong_answers=0,
        time_started=datetime.now(timezone.utc),
        is_completed=False
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    # Return first question (without correct answer)
    first_question = {
        "question": questions[0]["question"],
        "options": questions[0]["options"],
        "category": questions[0]["category"]
    }

    return StartGameResponse(
        game_id=game.id,
        category=game.category,
        difficulty=game.difficulty,
        total_questions=game.total_questions,
        first_question=first_question,
        current_index=0,
        message=f"Game started! Good luck with {game.total_questions} questions!"
    )


@router.post("/games/{game_id}/answer", response_model=SubmitAnswerResponse)
def submit_answer(
    game_id: int,
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Submit an answer for the current question

    Returns whether the answer was correct and provides the next question
    or final stats if the game is complete.
    """
    # Get game
    game = db.query(TriviaGame).filter(
        TriviaGame.id == game_id,
        TriviaGame.user_id == user_id
    ).first()

    if not game:
        raise HTTPException(404, "Game not found")

    if game.is_completed:
        raise HTTPException(400, "Game already completed")

    # Ensure questions_data is a list (SQLite JSON can return string)
    questions = game.questions_data
    if isinstance(questions, str):
        import json
        questions = json.loads(questions)

    # Get current question
    current_index = game.current_question_index
    if current_index >= len(questions):
        raise HTTPException(400, f"No more questions available (index {current_index}, total {len(questions)})")

    current_question = questions[current_index]
    correct_answer_index = current_question["correct_answer"]
    is_correct = request.selected_answer == correct_answer_index

    # Calculate points (10 points per correct answer)
    points_earned = 10 if is_correct else 0

    # Save answer
    answer = TriviaAnswer(
        game_id=game.id,
        question_index=current_index,
        question_text=current_question["question"],
        selected_answer=request.selected_answer,
        correct_answer=correct_answer_index,
        is_correct=is_correct,
        time_taken_seconds=request.time_taken_seconds,
        answered_at=datetime.now(timezone.utc)
    )
    db.add(answer)

    # Update game stats
    game.score += points_earned
    if is_correct:
        game.correct_answers += 1
    else:
        game.wrong_answers += 1

    game.current_question_index += 1

    # Check if game is complete
    game_completed = game.current_question_index >= game.total_questions
    next_question = None
    final_stats = None

    if game_completed:
        # Complete the game
        game.is_completed = True
        game.time_completed = datetime.now(timezone.utc)

        # Calculate time taken - handle SQLite datetime string
        try:
            time_started = game.time_started
            if isinstance(time_started, str):
                from datetime import datetime as dt
                # Try common SQLite datetime formats
                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        time_started = dt.strptime(time_started, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
            if isinstance(time_started, datetime):
                time_completed = game.time_completed
                # Ensure both are tz-aware or both naive for subtraction
                if time_started.tzinfo is None:
                    time_started = time_started.replace(tzinfo=timezone.utc)
                if time_completed.tzinfo is None:
                    time_completed = time_completed.replace(tzinfo=timezone.utc)
                game.time_taken_seconds = int((time_completed - time_started).total_seconds())
            else:
                game.time_taken_seconds = 0
        except Exception as e:
            print(f"Error calculating time: {e}")
            game.time_taken_seconds = 0

        # Prepare final stats
        accuracy = int((game.correct_answers / game.total_questions) * 100)
        final_stats = {
            "score": game.score,
            "correct": game.correct_answers,
            "wrong": game.wrong_answers,
            "total": game.total_questions,
            "accuracy": accuracy,
            "time_taken": game.time_taken_seconds or 0
        }

        # Commit game completion first, then update leaderboard
        db.commit()

        try:
            update_leaderboard(db, user_id, game)
        except Exception as e:
            print(f"Leaderboard update error (non-fatal): {e}")
    else:
        # Get next question (without correct answer)
        next_q = questions[game.current_question_index]
        next_question = {
            "question": next_q["question"],
            "options": next_q["options"],
            "category": next_q["category"],
            "question_number": game.current_question_index + 1
        }

    db.commit()

    return SubmitAnswerResponse(
        is_correct=is_correct,
        correct_answer=correct_answer_index,
        explanation=current_question["explanation"],
        current_score=game.score,
        correct_count=game.correct_answers,
        wrong_count=game.wrong_answers,
        next_question=next_question,
        game_completed=game_completed,
        final_stats=final_stats
    )


@router.get("/games/{game_id}/stats", response_model=GameStats)
def get_game_stats(
    game_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get statistics for a specific game"""
    game = db.query(TriviaGame).filter(
        TriviaGame.id == game_id,
        TriviaGame.user_id == user_id
    ).first()

    if not game:
        raise HTTPException(404, "Game not found")

    accuracy = 0
    if game.total_questions > 0:
        accuracy = int((game.correct_answers / game.total_questions) * 100)

    return GameStats(
        game_id=game.id,
        score=game.score,
        correct_answers=game.correct_answers,
        wrong_answers=game.wrong_answers,
        total_questions=game.total_questions,
        accuracy=accuracy,
        time_taken_seconds=game.time_taken_seconds,
        category=game.category
    )


@router.get("/leaderboard/{category}", response_model=LeaderboardResponse)
def get_leaderboard(
    category: str = "general",
    limit: int = 10,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get leaderboard for a specific category

    Returns top players ranked by best score, then accuracy.
    """
    # Import User model
    from models.user import User

    # Get top entries
    entries_query = db.query(
        TriviaLeaderboard,
        User.username
    ).join(
        User, TriviaLeaderboard.user_id == User.id
    ).filter(
        TriviaLeaderboard.category == category
    ).order_by(
        desc(TriviaLeaderboard.best_score),
        desc(TriviaLeaderboard.best_accuracy)
    ).limit(limit)

    entries = []
    user_rank = None
    rank = 1

    for leaderboard, username in entries_query:
        entries.append(LeaderboardEntry(
            rank=rank,
            user_id=leaderboard.user_id,
            username=username,
            best_score=leaderboard.best_score,
            best_accuracy=leaderboard.best_accuracy,
            total_games=leaderboard.total_games_played,
            fastest_time=leaderboard.fastest_game_seconds
        ))

        if leaderboard.user_id == user_id:
            user_rank = rank

        rank += 1

    # Get total players count
    total_players = db.query(TriviaLeaderboard).filter(
        TriviaLeaderboard.category == category
    ).count()

    return LeaderboardResponse(
        category=category,
        entries=entries,
        user_rank=user_rank,
        total_players=total_players
    )


def update_leaderboard(db: Session, user_id: int, game: TriviaGame):
    """Update leaderboard entry for a user"""
    leaderboard = db.query(TriviaLeaderboard).filter(
        TriviaLeaderboard.user_id == user_id,
        TriviaLeaderboard.category == game.category
    ).first()

    accuracy = int((game.correct_answers / game.total_questions) * 100)

    if not leaderboard:
        # Create new leaderboard entry
        leaderboard = TriviaLeaderboard(
            user_id=user_id,
            category=game.category,
            best_score=game.score,
            best_accuracy=accuracy,
            total_games_played=1,
            total_questions_answered=game.total_questions,
            total_correct_answers=game.correct_answers,
            fastest_game_seconds=game.time_taken_seconds,
            last_played=datetime.now(timezone.utc)
        )
        db.add(leaderboard)
    else:
        # Update existing entry
        leaderboard.total_games_played += 1
        leaderboard.total_questions_answered += game.total_questions
        leaderboard.total_correct_answers += game.correct_answers
        leaderboard.last_played = datetime.now(timezone.utc)

        # Update best score if improved
        if game.score > leaderboard.best_score:
            leaderboard.best_score = game.score

        # Update best accuracy if improved
        if accuracy > leaderboard.best_accuracy:
            leaderboard.best_accuracy = accuracy

        # Update fastest time
        if game.time_taken_seconds:
            if not leaderboard.fastest_game_seconds or game.time_taken_seconds < leaderboard.fastest_game_seconds:
                leaderboard.fastest_game_seconds = game.time_taken_seconds

    db.commit()
