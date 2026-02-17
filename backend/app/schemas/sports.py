"""
Pydantic schemas for sports betting API
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class BetTypeEnum(str, Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"


class BetSelectionEnum(str, Enum):
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"
    OVER = "over"
    UNDER = "under"


class BetStatusEnum(str, Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    PUSH = "push"
    CANCELLED = "cancelled"


class MatchStatusEnum(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Odds display schemas
class MoneylineOdds(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None
    draw: Optional[int] = None


class SpreadOdds(BaseModel):
    home: Optional[Dict[str, float]] = None  # {"point": -7.5, "odds": -110}
    away: Optional[Dict[str, float]] = None


class TotalOdds(BaseModel):
    over: Optional[Dict[str, float]] = None  # {"point": 215.5, "odds": -110}
    under: Optional[Dict[str, float]] = None


class MatchOddsResponse(BaseModel):
    """Response for a single match with odds"""
    event_id: str
    match_id: Optional[int] = None  # DB ID (if saved)
    sport_key: str
    sport_title: str
    home_team: str
    away_team: str
    commence_time: datetime
    status: MatchStatusEnum

    # Odds
    moneyline: MoneylineOdds
    spreads: SpreadOdds
    totals: TotalOdds

    # Results (if completed)
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    class Config:
        from_attributes = True


class TodaysGamesResponse(BaseModel):
    """Response for today's games grouped by category"""
    category: str  # football, basketball, etc.
    sport_key: str  # basketball_nba, etc.
    sport_title: str  # NBA
    games: List[MatchOddsResponse]
    total_games: int


# Bet placement schemas
class BetPickRequest(BaseModel):
    """Single pick within a bet"""
    match_id: int  # DB match ID
    bet_type: BetTypeEnum
    selection: BetSelectionEnum
    odds: int  # American odds
    point: Optional[float] = None  # For spreads/totals

    @validator('point')
    def validate_point_for_type(cls, v, values):
        """Ensure point is provided for spread and total bets"""
        bet_type = values.get('bet_type')
        if bet_type in [BetTypeEnum.SPREAD, BetTypeEnum.TOTAL] and v is None:
            raise ValueError(f"Point value required for {bet_type} bets")
        return v


class PlaceBetRequest(BaseModel):
    """Request to place a bet (single or parlay)"""
    picks: List[BetPickRequest] = Field(..., min_items=1, max_items=10)
    stake: int = Field(default=10, ge=1, le=1000)  # Virtual points to wager

    @validator('picks')
    def validate_picks(cls, v):
        """Ensure picks are valid"""
        if len(v) < 1:
            raise ValueError("At least one pick required")
        if len(v) > 10:
            raise ValueError("Maximum 10 picks per bet (parlay)")

        # Ensure no duplicate matches
        match_ids = [pick.match_id for pick in v]
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("Cannot place multiple picks on the same match")

        return v


class BetPickResponse(BaseModel):
    """Single pick in a bet (response)"""
    id: int
    match_id: int
    match_description: str  # "Lakers vs Warriors"
    bet_type: BetTypeEnum
    selection: BetSelectionEnum
    odds: int
    point: Optional[float] = None
    result: Optional[BetStatusEnum] = None

    class Config:
        from_attributes = True


class BetResponse(BaseModel):
    """Response for a placed bet"""
    id: int
    user_id: int
    is_parlay: bool
    total_picks: int
    stake: int
    potential_payout: float
    actual_payout: float
    status: BetStatusEnum
    placed_at: datetime
    settled_at: Optional[datetime] = None

    # Picks in this bet
    picks: List[BetPickResponse]

    class Config:
        from_attributes = True


class UserBetsResponse(BaseModel):
    """User's betting history"""
    active_bets: List[BetResponse]  # Pending
    settled_bets: List[BetResponse]  # Won/Lost/Push
    total_active: int
    total_settled: int


# Leaderboard schemas
class LeaderboardEntry(BaseModel):
    """Single entry in leaderboard"""
    rank: int
    user_id: int
    username: str
    total_bets: int
    bets_won: int
    win_percentage: float
    net_profit: int
    current_streak: int
    best_win_streak: int

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Leaderboard for a sport category"""
    sport_category: str
    entries: List[LeaderboardEntry]
    total_entries: int
    user_rank: Optional[int] = None  # Requesting user's rank


class UserStatsResponse(BaseModel):
    """User's personal betting statistics"""
    user_id: int
    username: str

    # Overall
    total_bets: int
    total_parlays: int
    total_wagered: int
    total_won: int
    net_profit: int

    # Performance
    win_percentage: float
    current_streak: int
    best_win_streak: int
    biggest_win: float

    # By sport category
    stats_by_sport: Dict[str, Dict[str, Any]]  # {"football": {...}, "basketball": {...}}

    class Config:
        from_attributes = True


# Admin schemas
class UpdateMatchResultRequest(BaseModel):
    """Admin request to update match result"""
    match_id: int
    home_score: int
    away_score: int
    status: MatchStatusEnum = MatchStatusEnum.COMPLETED
