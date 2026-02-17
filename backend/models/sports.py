"""
Sports Betting Models
Supports single bets and parlays (multiple picks in one bet)
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
import enum


class BetType(str, enum.Enum):
    """Types of bets users can place"""
    MONEYLINE = "moneyline"  # Pick winner
    SPREAD = "spread"        # Point spread
    TOTAL = "total"          # Over/under


class BetSelection(str, enum.Enum):
    """User's selection for the bet"""
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"
    OVER = "over"
    UNDER = "under"


class BetStatus(str, enum.Enum):
    """Status of a bet"""
    PENDING = "pending"      # Waiting for game(s) to complete
    WON = "won"             # All picks correct
    LOST = "lost"           # At least one pick wrong
    PUSH = "push"           # Tie (rare, spreads/totals only)
    CANCELLED = "cancelled"  # Game cancelled


class MatchStatus(str, enum.Enum):
    """Status of a sports match"""
    UPCOMING = "upcoming"    # Not started yet
    LIVE = "live"           # In progress
    COMPLETED = "completed"  # Finished
    CANCELLED = "cancelled"  # Cancelled


class SportsMatch(Base):
    """
    Master data for sports events/games
    Populated from The Odds API
    """
    __tablename__ = "sports_matches"

    id = Column(Integer, primary_key=True, index=True)

    # External API identifiers
    external_id = Column(String(255), unique=True, nullable=False, index=True)  # API event ID
    sport_key = Column(String(100), nullable=False, index=True)  # e.g., 'basketball_nba'
    sport_title = Column(String(100), nullable=False)  # e.g., 'NBA'

    # Teams
    home_team = Column(String(255), nullable=False)
    away_team = Column(String(255), nullable=False)

    # Timing
    commence_time = Column(DateTime, nullable=False, index=True)  # When game starts
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.UPCOMING, nullable=False, index=True)

    # Odds data (raw from API)
    odds_data = Column(JSON, nullable=True)  # Full bookmaker odds

    # Results (populated after game completes)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    picks = relationship("BetPick", back_populates="match", cascade="all, delete-orphan")


class Bet(Base):
    """
    A bet placed by a user (can be single or parlay)
    Parlay = multiple picks in one bet
    """
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Bet configuration
    is_parlay = Column(Boolean, default=False, nullable=False)  # True if multiple picks
    total_picks = Column(Integer, default=1, nullable=False)  # Number of picks in this bet

    # Wagering
    stake = Column(Integer, default=10, nullable=False)  # Virtual points wagered
    potential_payout = Column(Float, default=0.0, nullable=False)  # Calculated from odds
    actual_payout = Column(Float, default=0.0, nullable=False)  # After bet settles

    # Status
    status = Column(SQLEnum(BetStatus), default=BetStatus.PENDING, nullable=False, index=True)

    # Tracking
    placed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    settled_at = Column(DateTime, nullable=True)  # When bet result determined

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    picks = relationship("BetPick", back_populates="bet", cascade="all, delete-orphan")


class BetPick(Base):
    """
    Individual pick within a bet
    For single bets: 1 pick per bet
    For parlays: multiple picks per bet (all must win)
    """
    __tablename__ = "bet_picks"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("sports_matches.id"), nullable=False, index=True)

    # Pick details
    bet_type = Column(SQLEnum(BetType), nullable=False)  # moneyline, spread, total
    selection = Column(SQLEnum(BetSelection), nullable=False)  # home, away, over, under, draw

    # Odds at time of bet
    odds = Column(Integer, nullable=False)  # American odds (e.g., +150, -110)
    point = Column(Float, nullable=True)  # For spreads and totals (e.g., -7.5, 215.5)

    # Result
    result = Column(SQLEnum(BetStatus), nullable=True, index=True)  # won, lost, push, cancelled

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    bet = relationship("Bet", back_populates="picks")
    match = relationship("SportsMatch", back_populates="picks")

    # Ensure user can't bet same pick twice in one bet
    __table_args__ = (
        UniqueConstraint('bet_id', 'match_id', 'bet_type', 'selection', name='unique_pick_per_bet'),
    )


class SportsLeaderboard(Base):
    """
    Aggregate leaderboard tracking for sports betting
    One row per user per sport category (football, basketball, etc.)
    """
    __tablename__ = "sports_leaderboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sport_category = Column(String(50), nullable=False, index=True)  # football, basketball, baseball, hockey, soccer

    # Overall stats
    total_bets = Column(Integer, default=0, nullable=False)
    total_parlays = Column(Integer, default=0, nullable=False)

    # Win/loss record
    bets_won = Column(Integer, default=0, nullable=False)
    bets_lost = Column(Integer, default=0, nullable=False)
    bets_pushed = Column(Integer, default=0, nullable=False)

    # Points tracking
    total_wagered = Column(Integer, default=0, nullable=False)
    total_won = Column(Integer, default=0, nullable=False)
    net_profit = Column(Integer, default=0, nullable=False)  # total_won - total_wagered

    # Accuracy
    win_percentage = Column(Float, default=0.0, nullable=False)

    # Streaks
    current_streak = Column(Integer, default=0, nullable=False)  # Positive = wins, negative = losses
    best_win_streak = Column(Integer, default=0, nullable=False)
    worst_loss_streak = Column(Integer, default=0, nullable=False)

    # Best performance
    biggest_win = Column(Float, default=0.0, nullable=False)
    biggest_parlay_hits = Column(Integer, default=0, nullable=False)  # Most legs in successful parlay

    # Activity
    last_bet_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # One leaderboard entry per user per sport category
    __table_args__ = (
        UniqueConstraint('user_id', 'sport_category', name='unique_user_sport_leaderboard'),
    )
