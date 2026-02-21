"""
User profile, dashboard, and friends API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from jose import jwt, JWTError
import uuid
import io

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.user import User, UserProfile
from models.trivia import TriviaGame, TriviaLeaderboard
from models.friends import Friendship

router = APIRouter(prefix="/api", tags=["user"])

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-for-development")
ALGORITHM = "HS256"


def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Extract user ID from JWT token in Authorization header"""
    if not authorization:
        return 1  # Fallback for testing
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return 1
        return int(user_id)
    except (JWTError, ValueError):
        return 1


# --- S3 helper ---

def _upload_avatar_to_s3(file_bytes: bytes, content_type: str, user_id: int) -> str:
    """Upload avatar image to S3-compatible bucket, return public URL."""
    import boto3
    from botocore.client import Config

    # Support both AWS_* (Railway native) and S3_* names
    bucket   = os.getenv("S3_BUCKET_NAME", "")
    endpoint = os.getenv("AWS_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL", "")
    region   = os.getenv("AWS_DEFAULT_REGION") or os.getenv("S3_REGION", "us-east-1")
    pub_url  = os.getenv("S3_PUBLIC_URL", "")  # optional CDN base URL

    if not bucket:
        raise HTTPException(500, "S3_BUCKET_NAME not configured")

    ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
    key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"

    kwargs = dict(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_ACCESS_KEY"),
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    if endpoint:
        kwargs["endpoint_url"] = endpoint

    s3 = boto3.client("s3", **kwargs)
    s3.upload_fileobj(
        io.BytesIO(file_bytes),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
    )

    if pub_url:
        return f"{pub_url.rstrip('/')}/{key}"
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


# --- Schemas ---

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

class AddFriendRequest(BaseModel):
    username: str


class FriendInfo(BaseModel):
    friend_id: int
    user_id: int
    username: str
    total_games: int


class FriendsListResponse(BaseModel):
    friends: list


class DashboardResponse(BaseModel):
    total_games: int
    avg_accuracy: int
    total_score: int
    friend_count: int
    recent_games: list


class ProfileResponse(BaseModel):
    total_games: int
    total_score: int
    avg_accuracy: int
    best_accuracy: int
    total_correct: int
    total_questions_answered: int
    category_stats: list
    game_history: list


# --- Dashboard ---

@router.get("/user/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get dashboard data: stats overview, recent games, friend count"""
    # Get completed games
    games = db.query(TriviaGame).filter(
        TriviaGame.user_id == user_id,
        TriviaGame.is_completed == True
    ).order_by(desc(TriviaGame.time_completed)).all()

    total_games = len(games)
    total_score = sum(g.score for g in games)
    total_correct = sum(g.correct_answers for g in games)
    total_questions = sum(g.total_questions for g in games)
    avg_accuracy = int((total_correct / total_questions * 100)) if total_questions > 0 else 0

    # Friend count
    friend_count = db.query(Friendship).filter(
        Friendship.user_id == user_id
    ).count()

    # Recent games (last 5)
    recent_games = []
    for g in games[:5]:
        accuracy = int((g.correct_answers / g.total_questions * 100)) if g.total_questions > 0 else 0
        recent_games.append({
            "game_id": g.id,
            "category": g.category,
            "score": g.score,
            "accuracy": accuracy,
            "total_questions": g.total_questions,
            "played_at": g.time_completed.isoformat() if g.time_completed else None
        })

    return {
        "total_games": total_games,
        "avg_accuracy": avg_accuracy,
        "total_score": total_score,
        "friend_count": friend_count,
        "recent_games": recent_games
    }


# --- Profile ---

@router.get("/user/profile")
def get_profile(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get detailed profile with stats by category and game history"""
    games = db.query(TriviaGame).filter(
        TriviaGame.user_id == user_id,
        TriviaGame.is_completed == True
    ).order_by(desc(TriviaGame.time_completed)).all()

    total_games = len(games)
    total_score = sum(g.score for g in games)
    total_correct = sum(g.correct_answers for g in games)
    total_questions = sum(g.total_questions for g in games)
    avg_accuracy = int((total_correct / total_questions * 100)) if total_questions > 0 else 0
    best_accuracy = 0

    # Category breakdown
    cat_data = {}
    for g in games:
        acc = int((g.correct_answers / g.total_questions * 100)) if g.total_questions > 0 else 0
        if acc > best_accuracy:
            best_accuracy = acc
        if g.category not in cat_data:
            cat_data[g.category] = {"games": 0, "correct": 0, "total": 0, "best_score": 0}
        cat_data[g.category]["games"] += 1
        cat_data[g.category]["correct"] += g.correct_answers
        cat_data[g.category]["total"] += g.total_questions
        if g.score > cat_data[g.category]["best_score"]:
            cat_data[g.category]["best_score"] = g.score

    category_stats = []
    for cat, data in cat_data.items():
        cat_acc = int((data["correct"] / data["total"] * 100)) if data["total"] > 0 else 0
        category_stats.append({
            "category": cat,
            "games": data["games"],
            "accuracy": cat_acc,
            "best_score": data["best_score"]
        })

    # Game history (last 20)
    game_history = []
    for g in games[:20]:
        acc = int((g.correct_answers / g.total_questions * 100)) if g.total_questions > 0 else 0
        game_history.append({
            "game_id": g.id,
            "category": g.category,
            "score": g.score,
            "correct": g.correct_answers,
            "total": g.total_questions,
            "accuracy": acc,
            "time_taken": g.time_taken_seconds,
            "played_at": g.time_completed.isoformat() if g.time_completed else None
        })

    return {
        "total_games": total_games,
        "total_score": total_score,
        "avg_accuracy": avg_accuracy,
        "best_accuracy": best_accuracy,
        "total_correct": total_correct,
        "total_questions_answered": total_questions,
        "category_stats": category_stats,
        "game_history": game_history
    }


# --- Profile update ---

@router.patch("/user/profile")
def update_profile(
    data: UpdateProfileRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update first_name, last_name, bio."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if data.first_name is not None:
        user.first_name = data.first_name.strip() or None
    if data.last_name is not None:
        user.last_name = data.last_name.strip() or None
    if data.bio is not None:
        user.bio = data.bio.strip()[:500] or None
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "auth_provider": user.auth_provider,
        "email_verified": user.email_verified,
    }


@router.post("/user/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Upload a profile avatar image. Returns the new avatar URL."""
    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only JPEG, PNG, GIF, and WEBP images are allowed")

    max_bytes = 5 * 1024 * 1024  # 5 MB
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(400, "Image must be under 5 MB")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    try:
        avatar_url = _upload_avatar_to_s3(file_bytes, file.content_type, user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

    user.avatar_url = avatar_url
    db.commit()

    return {"avatar_url": avatar_url}


# --- Friends ---

@router.get("/friends")
def get_friends(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get list of friends with their stats"""
    friendships = db.query(Friendship).filter(
        Friendship.user_id == user_id
    ).all()

    friends = []
    for f in friendships:
        friend_user = db.query(User).filter(User.id == f.friend_id).first()
        if friend_user:
            # Get friend's game count
            game_count = db.query(TriviaGame).filter(
                TriviaGame.user_id == f.friend_id,
                TriviaGame.is_completed == True
            ).count()
            friends.append({
                "friend_id": f.id,
                "user_id": friend_user.id,
                "username": friend_user.username,
                "total_games": game_count
            })

    return {"friends": friends}


@router.post("/friends/add")
def add_friend(
    request: AddFriendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Add a friend by username"""
    # Find the friend user
    friend_user = db.query(User).filter(User.username == request.username).first()
    if not friend_user:
        raise HTTPException(404, "User not found")

    if friend_user.id == user_id:
        raise HTTPException(400, "You can't add yourself as a friend")

    # Check if already friends
    existing = db.query(Friendship).filter(
        Friendship.user_id == user_id,
        Friendship.friend_id == friend_user.id
    ).first()
    if existing:
        raise HTTPException(400, "Already friends with this user")

    # Create bidirectional friendship
    friendship1 = Friendship(user_id=user_id, friend_id=friend_user.id)
    friendship2 = Friendship(user_id=friend_user.id, friend_id=user_id)
    db.add(friendship1)
    db.add(friendship2)
    db.commit()

    return {"message": f"Added {request.username} as a friend!", "friend_id": friend_user.id}


@router.delete("/friends/{friendship_id}")
def remove_friend(
    friendship_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Remove a friend"""
    friendship = db.query(Friendship).filter(
        Friendship.id == friendship_id,
        Friendship.user_id == user_id
    ).first()

    if not friendship:
        raise HTTPException(404, "Friendship not found")

    # Remove both directions
    reverse = db.query(Friendship).filter(
        Friendship.user_id == friendship.friend_id,
        Friendship.friend_id == user_id
    ).first()

    db.delete(friendship)
    if reverse:
        db.delete(reverse)
    db.commit()

    return {"message": "Friend removed"}
