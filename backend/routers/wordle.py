from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.wordle import WordleGame, WordleStats
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import random

router = APIRouter(prefix="/api/wordle", tags=["wordle"])

# Wordle word list (5-letter common words)
WORDLE_WORDS = [
    "about", "above", "actor", "acute", "admit", "adopt", "adult", "after", "again", "agent",
    "agree", "ahead", "alarm", "album", "alert", "align", "alike", "alive", "allow", "alone",
    "along", "alter", "angel", "anger", "angle", "angry", "apart", "apple", "apply", "arena",
    "argue", "arise", "array", "aside", "asset", "avoid", "award", "aware", "badly", "baker",
    "basic", "basis", "beach", "began", "begin", "being", "below", "bench", "billy", "birth",
    "black", "blade", "blame", "blank", "blast", "bleed", "blend", "bless", "blind", "block",
    "blood", "bloom", "board", "boost", "booth", "bound", "brain", "brand", "bread", "break",
    "breed", "brief", "bring", "broad", "broke", "brown", "build", "built", "buyer", "cable",
    "calif", "carry", "catch", "cause", "chain", "chair", "chart", "chase", "cheap", "check",
    "chess", "chest", "chief", "child", "china", "chose", "civil", "claim", "class", "clean",
    "clear", "click", "climb", "clock", "close", "coach", "coast", "could", "count", "court",
    "cover", "crack", "craft", "crash", "crazy", "cream", "crime", "cross", "crowd", "crown",
    "curve", "cycle", "daily", "dance", "dated", "dealt", "death", "debut", "delay", "depth",
    "doing", "doubt", "dozen", "draft", "drama", "drank", "drawn", "dream", "dress", "drill",
    "drink", "drive", "drove", "dying", "eager", "early", "earth", "eight", "elect", "empty",
    "enemy", "enjoy", "enter", "entry", "equal", "error", "event", "every", "exact", "exist",
    "extra", "faith", "false", "fault", "fiber", "field", "fifth", "fifty", "fight", "final",
    "first", "fixed", "flash", "fleet", "floor", "fluid", "focus", "force", "forth", "forty",
    "forum", "found", "frame", "frank", "fraud", "fresh", "front", "fruit", "fully", "funny",
    "giant", "given", "glass", "globe", "going", "grace", "grade", "grand", "grant", "grass",
    "great", "green", "gross", "group", "grown", "guard", "guess", "guest", "guide", "happy",
    "harry", "heart", "heavy", "hence", "henry", "horse", "hotel", "house", "human", "ideal",
    "image", "imply", "index", "inner", "input", "issue", "japan", "jimmy", "joint", "jones",
    "judge", "known", "label", "large", "laser", "later", "laugh", "layer", "learn", "lease",
    "least", "leave", "legal", "lemon", "level", "lewis", "light", "limit", "links", "lives",
    "local", "logic", "loose", "lower", "lucky", "lunch", "lying", "magic", "major", "maker",
    "march", "maria", "match", "maybe", "mayor", "meant", "media", "metal", "might", "minor",
    "minus", "mixed", "model", "money", "month", "moral", "motor", "mount", "mouse", "mouth",
    "movie", "music", "needs", "never", "newly", "night", "noise", "north", "noted", "novel",
    "nurse", "occur", "ocean", "offer", "often", "order", "other", "ought", "paint", "panel",
    "panic", "paper", "party", "pause", "peace", "peter", "phase", "phone", "photo", "piece",
    "pilot", "pitch", "place", "plain", "plane", "plant", "plate", "point", "pound", "power",
    "press", "price", "pride", "prime", "print", "prior", "prize", "proof", "proud", "prove",
    "queen", "quick", "quiet", "quite", "radio", "raise", "range", "rapid", "ratio", "reach",
    "ready", "refer", "relax", "reply", "right", "rival", "river", "robin", "roger", "roman",
    "rough", "round", "route", "royal", "rural", "scale", "scene", "scope", "score", "sense",
    "serve", "seven", "shall", "shape", "share", "sharp", "sheet", "shelf", "shell", "shift",
    "shine", "shirt", "shock", "shoot", "short", "shown", "sight", "since", "sixth", "sixty",
    "sized", "skill", "sleep", "slide", "small", "smart", "smile", "smith", "smoke", "solid",
    "solve", "sorry", "sound", "south", "space", "spare", "speak", "speed", "spend", "spent",
    "split", "spoke", "sport", "staff", "stage", "stake", "stand", "start", "state", "steam",
    "steel", "stick", "still", "stock", "stone", "stood", "store", "storm", "story", "strip",
    "stuck", "study", "stuff", "style", "sugar", "suite", "sunny", "super", "sweet", "table",
    "taken", "taste", "taxes", "teach", "terry", "texas", "thank", "theft", "their", "theme",
    "there", "these", "thick", "thing", "think", "third", "those", "three", "threw", "throw",
    "tight", "times", "title", "today", "topic", "total", "touch", "tough", "tower", "track",
    "trade", "train", "treat", "trend", "trial", "tribe", "trick", "tried", "tries", "truck",
    "truly", "trust", "truth", "twice", "under", "undue", "union", "unity", "until", "upper",
    "upset", "urban", "usage", "usual", "valid", "value", "video", "virus", "visit", "vital",
    "vocal", "voice", "waste", "watch", "water", "wheel", "where", "which", "while", "white",
    "whole", "whose", "woman", "women", "world", "worry", "worse", "worst", "worth", "would",
    "wound", "write", "wrong", "wrote", "young", "youth"
]

# Valid guesses (includes all wordle words plus common 5-letter words)
VALID_GUESSES = set(WORDLE_WORDS + [
    "aargh", "abaca", "abaci", "aback", "abaft", "abase", "abash", "abate", "abbey", "abbot",
    "abhor", "abide", "abled", "abode", "abort", "abound", "abuse", "abyss", "ached", "aches",
    "acids", "acorn", "acrid", "acted", "adage", "adapt", "added", "adder", "adept", "adieu",
    "adios", "adlib", "admin", "adobe", "afoot", "afore", "afoul", "AfterCare", "agape", "agate",
    # ... add more valid words as needed
])

class GuessRequest(BaseModel):
    guess: str

class GuessResult(BaseModel):
    guess: str
    result: List[str]  # ["correct", "present", "absent"] for each letter
    is_won: bool
    is_game_over: bool
    attempts_used: int
    max_attempts: int

class GameState(BaseModel):
    game_id: int
    guesses: List[dict]
    is_won: bool
    is_completed: bool
    attempts_used: int
    max_attempts: int
    target_word: Optional[str] = None  # Only shown when game is over

class StatsResponse(BaseModel):
    games_played: int
    games_won: int
    win_percentage: int
    current_streak: int
    max_streak: int
    guess_distribution: dict

def check_guess(guess: str, target: str) -> List[str]:
    """
    Check a guess against the target word.
    Returns a list of results for each letter: 'correct', 'present', 'absent'
    """
    guess = guess.lower()
    target = target.lower()
    result = ["absent"] * 5
    target_counts = {}

    # Count letters in target
    for letter in target:
        target_counts[letter] = target_counts.get(letter, 0) + 1

    # First pass: mark correct positions
    for i in range(5):
        if guess[i] == target[i]:
            result[i] = "correct"
            target_counts[guess[i]] -= 1

    # Second pass: mark present letters
    for i in range(5):
        if result[i] == "absent" and guess[i] in target and target_counts[guess[i]] > 0:
            result[i] = "present"
            target_counts[guess[i]] -= 1

    return result

@router.post("/start")
async def start_game(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a new Wordle game"""
    # Check if user has an active game
    active_game = db.query(WordleGame).filter(
        WordleGame.user_id == current_user.id,
        WordleGame.is_completed == False
    ).first()

    if active_game:
        return {
            "game_id": active_game.id,
            "guesses": active_game.guesses,
            "attempts_used": active_game.attempts_used,
            "max_attempts": active_game.max_attempts,
            "is_completed": active_game.is_completed,
            "is_won": active_game.is_won
        }

    # Create new game
    target_word = random.choice(WORDLE_WORDS).upper()

    new_game = WordleGame(
        user_id=current_user.id,
        target_word=target_word,
        guesses=[],
        max_attempts=6
    )
    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return {
        "game_id": new_game.id,
        "guesses": [],
        "attempts_used": 0,
        "max_attempts": 6,
        "is_completed": False,
        "is_won": False
    }

@router.post("/guess/{game_id}", response_model=GuessResult)
async def make_guess(
    game_id: int,
    request: GuessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a guess for a Wordle game"""
    # Get the game
    game = db.query(WordleGame).filter(
        WordleGame.id == game_id,
        WordleGame.user_id == current_user.id
    ).first()

    if not game:
        raise HTTPException(404, "Game not found")

    if game.is_completed:
        raise HTTPException(400, "Game is already completed")

    # Validate guess
    guess = request.guess.upper().strip()
    if len(guess) != 5:
        raise HTTPException(400, "Guess must be exactly 5 letters")

    if not guess.isalpha():
        raise HTTPException(400, "Guess must contain only letters")

    # Check if word is valid (optional - can be disabled for easier gameplay)
    # if guess.lower() not in VALID_GUESSES:
    #     raise HTTPException(400, "Not a valid word")

    # Check the guess
    result = check_guess(guess, game.target_word)

    # Update game state
    game.guesses.append({
        "guess": guess,
        "result": result
    })
    game.attempts_used += 1

    is_won = all(r == "correct" for r in result)
    is_game_over = is_won or game.attempts_used >= game.max_attempts

    if is_game_over:
        game.is_completed = True
        game.is_won = is_won
        game.time_completed = datetime.now(timezone.utc)

        # Calculate time taken
        time_started = game.time_started
        if isinstance(time_started, str):
            from datetime import datetime as dt
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    time_started = dt.strptime(time_started, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

        if isinstance(time_started, datetime):
            time_delta = game.time_completed - time_started
            game.time_taken_seconds = int(time_delta.total_seconds())

        # Update user stats
        update_user_stats(current_user.id, is_won, game.attempts_used, db)

    db.commit()

    return GuessResult(
        guess=guess,
        result=result,
        is_won=is_won,
        is_game_over=is_game_over,
        attempts_used=game.attempts_used,
        max_attempts=game.max_attempts
    )

@router.get("/game/{game_id}", response_model=GameState)
async def get_game_state(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current game state"""
    game = db.query(WordleGame).filter(
        WordleGame.id == game_id,
        WordleGame.user_id == current_user.id
    ).first()

    if not game:
        raise HTTPException(404, "Game not found")

    return GameState(
        game_id=game.id,
        guesses=game.guesses,
        is_won=game.is_won,
        is_completed=game.is_completed,
        attempts_used=game.attempts_used,
        max_attempts=game.max_attempts,
        target_word=game.target_word if game.is_completed else None
    )

@router.get("/stats", response_model=StatsResponse)
async def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's Wordle statistics"""
    stats = db.query(WordleStats).filter(WordleStats.user_id == current_user.id).first()

    if not stats:
        return StatsResponse(
            games_played=0,
            games_won=0,
            win_percentage=0,
            current_streak=0,
            max_streak=0,
            guess_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}
        )

    win_percentage = int((stats.games_won / stats.games_played * 100)) if stats.games_played > 0 else 0

    return StatsResponse(
        games_played=stats.games_played,
        games_won=stats.games_won,
        win_percentage=win_percentage,
        current_streak=stats.current_streak,
        max_streak=stats.max_streak,
        guess_distribution=stats.guess_distribution
    )

def update_user_stats(user_id: int, is_won: bool, attempts_used: int, db: Session):
    """Update user's Wordle statistics"""
    stats = db.query(WordleStats).filter(WordleStats.user_id == user_id).first()

    if not stats:
        stats = WordleStats(
            user_id=user_id,
            games_played=0,
            games_won=0,
            current_streak=0,
            max_streak=0,
            guess_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}
        )
        db.add(stats)

    # Update stats
    stats.games_played += 1

    if is_won:
        stats.games_won += 1
        stats.current_streak += 1
        stats.max_streak = max(stats.max_streak, stats.current_streak)

        # Update guess distribution
        dist = stats.guess_distribution
        dist[str(attempts_used)] = dist.get(str(attempts_used), 0) + 1
        stats.guess_distribution = dist
    else:
        stats.current_streak = 0

    stats.last_played = datetime.now(timezone.utc)
    db.commit()
