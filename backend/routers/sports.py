"""
Sports Betting Router
Sportsbook with single bets and parlays, powered by The Odds API
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.user import User
from models.sports import SportsMatch, Bet, BetPick, SportsLeaderboard, BetStatus, MatchStatus, BetType
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sports", tags=["sports"])


def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Extract user ID from JWT token"""
    if not authorization:
        return 1

    try:
        token = authorization.replace("Bearer ", "")
        from jose import jwt
        import os
        SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-for-development")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            return 1
        return int(user_id)
    except Exception:
        return 1


def is_admin(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)) -> bool:
    """Check if current user is an admin"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(403, "Admin access required")

    # Default admin users
    admin_usernames = ["svidthekid"]
    admin_emails = ["svidron.robert@gmail.com"]

    # Check if user is marked as admin OR is in the default admin list
    is_user_admin = (user.role == "admin" or
                     user.username in admin_usernames or
                     user.email in admin_emails)

    if not is_user_admin:
        raise HTTPException(403, "Admin access required")

    return True


# Pydantic schemas (inline for simplicity)
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


class MoneylineOdds(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None
    draw: Optional[int] = None


class SpreadOdds(BaseModel):
    home: Optional[Dict[str, float]] = None
    away: Optional[Dict[str, float]] = None


class TotalOdds(BaseModel):
    over: Optional[Dict[str, float]] = None
    under: Optional[Dict[str, float]] = None


class MatchOddsResponse(BaseModel):
    event_id: str
    match_id: Optional[int] = None
    sport_key: str
    sport_title: str
    home_team: str
    away_team: str
    commence_time: datetime
    moneyline: MoneylineOdds
    spreads: SpreadOdds
    totals: TotalOdds
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class TodaysGamesResponse(BaseModel):
    category: str
    sport_key: str
    sport_title: str
    games: List[MatchOddsResponse]


class BetPickRequest(BaseModel):
    match_id: int
    bet_type: BetTypeEnum
    selection: BetSelectionEnum
    odds: int
    point: Optional[float] = None


class PlaceBetRequest(BaseModel):
    picks: List[BetPickRequest] = Field(..., min_items=1, max_items=10)
    stake: int = Field(default=10, ge=1, le=1000)


class BetPickResponse(BaseModel):
    id: int
    match_id: int
    match_description: str
    bet_type: str
    selection: str
    odds: int
    point: Optional[float]
    result: Optional[str]


class BetResponse(BaseModel):
    id: int
    user_id: int
    is_parlay: bool
    total_picks: int
    stake: int
    potential_payout: float
    actual_payout: float
    status: str
    placed_at: datetime
    settled_at: Optional[datetime]
    picks: List[BetPickResponse]


# Helper functions
def calculate_payout(picks: List[BetPick], stake: int) -> float:
    """Calculate potential payout from American odds (parlays multiply)"""
    total_decimal_odds = 1.0
    for pick in picks:
        american_odds = pick.odds
        if american_odds > 0:
            decimal_odds = (american_odds / 100) + 1
        else:
            decimal_odds = (100 / abs(american_odds)) + 1
        total_decimal_odds *= decimal_odds
    return round(stake * total_decimal_odds, 2)


def determine_pick_result(pick: BetPick, match: SportsMatch) -> BetStatus:
    """Determine if a pick won, lost, or pushed"""
    if match.status != MatchStatus.COMPLETED or match.home_score is None:
        return BetStatus.PENDING

    home_score = match.home_score
    away_score = match.away_score

    if pick.bet_type == BetType.MONEYLINE:
        if home_score == away_score:
            return BetStatus.WON if pick.selection.value == "draw" else BetStatus.PUSH
        elif home_score > away_score:
            return BetStatus.WON if pick.selection.value == "home" else BetStatus.LOST
        else:
            return BetStatus.WON if pick.selection.value == "away" else BetStatus.LOST

    elif pick.bet_type == BetType.SPREAD:
        home_with_spread = home_score + pick.point
        if home_with_spread == away_score:
            return BetStatus.PUSH
        if pick.selection.value == "home":
            return BetStatus.WON if home_with_spread > away_score else BetStatus.LOST
        else:
            return BetStatus.WON if home_with_spread < away_score else BetStatus.LOST

    elif pick.bet_type == BetType.TOTAL:
        total_points = home_score + away_score
        if total_points == pick.point:
            return BetStatus.PUSH
        if pick.selection.value == "over":
            return BetStatus.WON if total_points > pick.point else BetStatus.LOST
        else:
            return BetStatus.WON if total_points < pick.point else BetStatus.LOST

    return BetStatus.PENDING


def update_leaderboard(db: Session, user_id: int, sport_category: str, bet: Bet):
    """Update user's leaderboard stats"""
    leaderboard = db.query(SportsLeaderboard).filter(
        SportsLeaderboard.user_id == user_id,
        SportsLeaderboard.sport_category == sport_category
    ).first()

    if not leaderboard:
        leaderboard = SportsLeaderboard(user_id=user_id, sport_category=sport_category)
        db.add(leaderboard)

    leaderboard.total_bets += 1
    if bet.is_parlay:
        leaderboard.total_parlays += 1

    leaderboard.total_wagered += bet.stake
    leaderboard.total_won += int(bet.actual_payout)
    leaderboard.net_profit = leaderboard.total_won - leaderboard.total_wagered

    if bet.status == BetStatus.WON:
        leaderboard.bets_won += 1
        leaderboard.current_streak = max(1, leaderboard.current_streak + 1) if leaderboard.current_streak >= 0 else 1
        leaderboard.best_win_streak = max(leaderboard.best_win_streak, leaderboard.current_streak)
        if bet.actual_payout > leaderboard.biggest_win:
            leaderboard.biggest_win = bet.actual_payout
    elif bet.status == BetStatus.LOST:
        leaderboard.bets_lost += 1
        leaderboard.current_streak = min(-1, leaderboard.current_streak - 1) if leaderboard.current_streak <= 0 else -1
    elif bet.status == BetStatus.PUSH:
        leaderboard.bets_pushed += 1

    total_decided = leaderboard.bets_won + leaderboard.bets_lost
    if total_decided > 0:
        leaderboard.win_percentage = round((leaderboard.bets_won / total_decided) * 100, 2)

    leaderboard.last_bet_at = datetime.now(timezone.utc)
    db.commit()


def settle_completed_matches(db: Session) -> dict:
    """
    Fetch scores from The Odds API for all sports we have matches for,
    update match results, and settle any pending bets.
    Returns summary counts. Safe to call repeatedly — skips already-settled bets.
    """
    import asyncio
    from app.services.odds_service import odds_service

    # Skip entirely if no pending bets exist
    pending_count = db.query(Bet).filter(Bet.status == BetStatus.PENDING).count()
    if pending_count == 0:
        logger.info("Settlement skipped — no pending bets")
        return {"matches_settled": 0, "bets_settled": 0, "skipped": True}

    try:
        all_scores = asyncio.run(odds_service.get_all_scores(days_from=1))
    except Exception as e:
        logger.error(f"Failed to fetch scores: {e}")
        return {"error": str(e), "matches_settled": 0, "bets_settled": 0}

    matches_settled = 0
    bets_settled = 0

    for sport_key, score_events in all_scores.items():
        for event in score_events:
            # Only process completed games that have scores
            completed = event.get("completed", False)
            scores = event.get("scores")
            if not completed or not scores:
                continue

            external_id = event.get("id")
            match = db.query(SportsMatch).filter(
                SportsMatch.external_id == external_id
            ).first()

            if not match:
                continue

            # Skip if already marked completed
            if match.status == MatchStatus.COMPLETED:
                continue

            # Parse home/away scores from the scores list
            home_score = None
            away_score = None
            for score_entry in scores:
                name = score_entry.get("name")
                score_val = score_entry.get("score")
                if score_val is None:
                    continue
                try:
                    score_int = int(score_val)
                except (ValueError, TypeError):
                    continue
                if name == match.home_team:
                    home_score = score_int
                elif name == match.away_team:
                    away_score = score_int

            if home_score is None or away_score is None:
                logger.warning(
                    f"Could not parse scores for {match.home_team} vs {match.away_team} "
                    f"(external_id={external_id})"
                )
                continue

            # Mark match completed
            match.home_score = home_score
            match.away_score = away_score
            match.status = MatchStatus.COMPLETED
            match.completed_at = datetime.now(timezone.utc)
            matches_settled += 1

            # Settle all pending picks for this match
            picks = db.query(BetPick).filter(BetPick.match_id == match.id).all()
            affected_bet_ids = set(p.bet_id for p in picks)

            for pick in picks:
                if pick.result is None:
                    pick.result = determine_pick_result(pick, match)

            # Evaluate each affected bet
            sport_category_map = {
                "basketball": ["basketball_nba", "basketball_ncaab", "basketball_wnba", "basketball_euroleague"],
                "football": ["americanfootball_nfl", "americanfootball_ncaaf", "americanfootball_cfl", "australianfootball_afl"],
                "baseball": ["baseball_mlb", "baseball_kbo", "baseball_npb"],
                "hockey": ["icehockey_nhl", "icehockey_ahl", "icehockey_shl", "icehockey_allsvenskan", "icehockey_liiga"],
                "soccer": ["soccer_epl", "soccer_germany_bundesliga", "soccer_spain_la_liga",
                           "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_brazil_campeonato",
                           "soccer_uefa_champs_league", "soccer_uefa_europa_league"],
            }

            for bet_id in affected_bet_ids:
                bet = db.query(Bet).get(bet_id)
                if not bet or bet.status != BetStatus.PENDING:
                    continue

                # A parlay is only fully settled when ALL picks have a result
                if any(p.result is None for p in bet.picks):
                    continue

                any_lost = any(p.result == BetStatus.LOST for p in bet.picks)
                all_won = all(p.result == BetStatus.WON for p in bet.picks)
                all_push = all(p.result == BetStatus.PUSH for p in bet.picks)

                if any_lost:
                    bet.status = BetStatus.LOST
                    bet.actual_payout = 0
                elif all_won:
                    bet.status = BetStatus.WON
                    bet.actual_payout = bet.potential_payout
                elif all_push:
                    bet.status = BetStatus.PUSH
                    bet.actual_payout = bet.stake
                else:
                    # Mixed push/win — treat pushed picks as 1.0x multiplier
                    # Recalculate payout using only non-push picks
                    won_picks = [p for p in bet.picks if p.result == BetStatus.WON]
                    if won_picks:
                        bet.status = BetStatus.WON
                        bet.actual_payout = calculate_payout(won_picks, bet.stake)
                    else:
                        bet.status = BetStatus.PUSH
                        bet.actual_payout = bet.stake

                bet.settled_at = datetime.now(timezone.utc)
                bets_settled += 1

                # Update leaderboard
                first_match = db.query(SportsMatch).get(bet.picks[0].match_id)
                sport_key_lb = first_match.sport_key if first_match else sport_key
                sport_category = "other"
                for cat, keys in sport_category_map.items():
                    if sport_key_lb in keys:
                        sport_category = cat
                        break
                update_leaderboard(db, bet.user_id, sport_category, bet)

        db.commit()

    logger.info(f"Settlement run complete: {matches_settled} matches, {bets_settled} bets settled")
    return {"matches_settled": matches_settled, "bets_settled": bets_settled}


# Endpoints
@router.get("/today")
def get_todays_games(category: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get today's games from database (NOT from API)
    Odds are synced automatically at 6 AM and 3 PM ET
    """
    try:
        from app.services.odds_service import odds_service

        # Get matches from database (upcoming and today's completed)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=12)

        query = db.query(SportsMatch).filter(
            SportsMatch.commence_time >= cutoff_time
        )

        # Filter by sport category if provided
        if category:
            # Map category to sport keys
            category_sports = {
                "football": ["americanfootball_nfl", "americanfootball_ncaaf", "americanfootball_cfl", "australianfootball_afl"],
                "basketball": ["basketball_nba", "basketball_ncaab", "basketball_wnba", "basketball_euroleague"],
                "baseball": ["baseball_mlb", "baseball_kbo", "baseball_npb"],
                "hockey": ["icehockey_nhl", "icehockey_ahl", "icehockey_shl", "icehockey_allsvenskan", "icehockey_liiga"],
                "soccer": ["soccer_epl", "soccer_germany_bundesliga", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_brazil_campeonato", "soccer_uefa_champs_league", "soccer_uefa_europa_league"]
            }

            if category in category_sports:
                query = query.filter(SportsMatch.sport_key.in_(category_sports[category]))

        matches = query.order_by(SportsMatch.commence_time).all()

        # Group by sport key
        games_by_sport = {}
        for match in matches:
            if match.sport_key not in games_by_sport:
                games_by_sport[match.sport_key] = []

            # Parse odds from stored odds_data
            parsed = odds_service.parse_odds_for_display({
                "id": match.external_id,
                "sport_key": match.sport_key,
                "sport_title": match.sport_title,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "commence_time": match.commence_time.isoformat(),
                "bookmakers": match.odds_data or []
            })

            game = MatchOddsResponse(
                event_id=match.external_id,
                match_id=match.id,
                sport_key=match.sport_key,
                sport_title=match.sport_title,
                home_team=match.home_team,
                away_team=match.away_team,
                commence_time=match.commence_time,
                moneyline=MoneylineOdds(**parsed["moneyline"]),
                spreads=SpreadOdds(**parsed["spreads"]),
                totals=TotalOdds(**parsed["totals"]),
                home_score=match.home_score,
                away_score=match.away_score
            )
            games_by_sport[match.sport_key].append(game)

        # Build response grouped by category
        response = []
        category_map = {
            "americanfootball_nfl": "football",
            "americanfootball_ncaaf": "football",
            "americanfootball_cfl": "football",
            "australianfootball_afl": "football",
            "basketball_nba": "basketball",
            "basketball_ncaab": "basketball",
            "basketball_wnba": "basketball",
            "basketball_euroleague": "basketball",
            "baseball_mlb": "baseball",
            "baseball_kbo": "baseball",
            "baseball_npb": "baseball",
            "icehockey_nhl": "hockey",
            "icehockey_ahl": "hockey",
            "icehockey_shl": "hockey",
            "icehockey_allsvenskan": "hockey",
            "icehockey_liiga": "hockey",
            "soccer_epl": "soccer",
            "soccer_germany_bundesliga": "soccer",
            "soccer_spain_la_liga": "soccer",
            "soccer_italy_serie_a": "soccer",
            "soccer_france_ligue_one": "soccer",
            "soccer_brazil_campeonato": "soccer",
            "soccer_uefa_champs_league": "soccer",
            "soccer_uefa_europa_league": "soccer"
        }

        for sport_key, games in games_by_sport.items():
            cat = category_map.get(sport_key, "other")
            response.append(TodaysGamesResponse(
                category=cat,
                sport_key=sport_key,
                sport_title=games[0].sport_title if games else sport_key.upper(),
                games=games
            ))

        return response

    except Exception as e:
        logger.error(f"Error fetching today's games from DB: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch games: {str(e)}")


@router.post("/bets", response_model=BetResponse)
async def place_bet(
    request: PlaceBetRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Place a bet (single or parlay)"""
    try:
        now = datetime.now(timezone.utc)
        match_ids = [pick.match_id for pick in request.picks]

        matches = db.query(SportsMatch).filter(SportsMatch.id.in_(match_ids)).all()

        if len(matches) != len(match_ids):
            raise HTTPException(400, "One or more matches not found")

        # Check if games have started
        for match in matches:
            # Ensure commence_time is timezone-aware for comparison
            commence_time = match.commence_time
            if commence_time.tzinfo is None:
                # If naive, assume UTC
                commence_time = commence_time.replace(tzinfo=timezone.utc)

            if commence_time <= now:
                raise HTTPException(400, f"Match {match.home_team} vs {match.away_team} has already started")

        # Create bet
        bet = Bet(
            user_id=user_id,
            is_parlay=len(request.picks) > 1,
            total_picks=len(request.picks),
            stake=request.stake,
            status=BetStatus.PENDING,
            potential_payout=0
        )
        db.add(bet)
        db.flush()

        # Create picks
        bet_picks = []
        for pick_req in request.picks:
            pick = BetPick(
                bet_id=bet.id,
                match_id=pick_req.match_id,
                bet_type=pick_req.bet_type.value,
                selection=pick_req.selection.value,
                odds=pick_req.odds,
                point=pick_req.point
            )
            db.add(pick)
            bet_picks.append(pick)

        bet.potential_payout = calculate_payout(bet_picks, request.stake)
        db.commit()
        db.refresh(bet)

        # Build response
        pick_responses = []
        for pick in bet.picks:
            match = db.query(SportsMatch).get(pick.match_id)
            pick_responses.append(BetPickResponse(
                id=pick.id,
                match_id=pick.match_id,
                match_description=f"{match.away_team} @ {match.home_team}",
                bet_type=pick.bet_type.value,
                selection=pick.selection.value,
                odds=pick.odds,
                point=pick.point,
                result=pick.result.value if pick.result else None
            ))

        return BetResponse(
            id=bet.id,
            user_id=bet.user_id,
            is_parlay=bet.is_parlay,
            total_picks=bet.total_picks,
            stake=bet.stake,
            potential_payout=bet.potential_payout,
            actual_payout=bet.actual_payout,
            status=bet.status.value,
            placed_at=bet.placed_at,
            settled_at=bet.settled_at,
            picks=pick_responses
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing bet: {str(e)}")
        db.rollback()
        raise HTTPException(500, f"Failed to place bet: {str(e)}")


@router.get("/bets/my")
def get_my_bets(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get user's bets"""
    bets = db.query(Bet).filter(Bet.user_id == user_id).order_by(desc(Bet.placed_at)).limit(50).all()

    result = []
    for bet in bets:
        pick_responses = []
        for pick in bet.picks:
            match = db.query(SportsMatch).get(pick.match_id)
            pick_responses.append(BetPickResponse(
                id=pick.id,
                match_id=pick.match_id,
                match_description=f"{match.away_team} @ {match.home_team}",
                bet_type=pick.bet_type.value,
                selection=pick.selection.value,
                odds=pick.odds,
                point=pick.point,
                result=pick.result.value if pick.result else None
            ))

        result.append(BetResponse(
            id=bet.id,
            user_id=bet.user_id,
            is_parlay=bet.is_parlay,
            total_picks=bet.total_picks,
            stake=bet.stake,
            potential_payout=bet.potential_payout,
            actual_payout=bet.actual_payout,
            status=bet.status.value,
            placed_at=bet.placed_at,
            settled_at=bet.settled_at,
            picks=pick_responses
        ))

    return {"bets": result, "total": len(result)}


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get the last sync time and status"""
    from models.sync_metadata import SyncMetadata
    from zoneinfo import ZoneInfo

    sync_meta = db.query(SyncMetadata).first()

    if not sync_meta or not sync_meta.last_sync_time:
        return {
            "last_sync_time": None,
            "status": "never",
            "games_synced": 0,
            "formatted_time": "Never synced"
        }

    # Convert to ET timezone for display
    et_tz = ZoneInfo("America/New_York")
    sync_time_et = sync_meta.last_sync_time.astimezone(et_tz)

    # Format like "Today at 3:00 PM ET" or "Feb 17 at 6:00 AM ET"
    now_et = datetime.now(et_tz)
    if sync_time_et.date() == now_et.date():
        formatted = f"Today at {sync_time_et.strftime('%-I:%M %p')} ET"
    elif sync_time_et.date() == (now_et.date() - timedelta(days=1)):
        formatted = f"Yesterday at {sync_time_et.strftime('%-I:%M %p')} ET"
    else:
        formatted = sync_time_et.strftime("%b %d at %-I:%M %p ET")

    return {
        "last_sync_time": sync_meta.last_sync_time.isoformat(),
        "status": sync_meta.sync_status,
        "games_synced": sync_meta.games_synced,
        "formatted_time": formatted
    }


@router.post("/admin/sync-matches")
async def sync_matches(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin-only: Manually sync matches from Odds API to database"""
    try:
        from app.services.odds_service import odds_service
        from models.sync_metadata import SyncMetadata

        # Get or create sync metadata
        sync_meta = db.query(SyncMetadata).first()
        if not sync_meta:
            sync_meta = SyncMetadata()
            db.add(sync_meta)
            db.flush()

        # Mark sync as running
        sync_meta.sync_status = "running"
        db.commit()

        # Fetch all sports odds
        if category:
            odds_data = await odds_service.get_odds_by_category(category)
            categories_to_sync = {category: odds_data}
        else:
            categories_to_sync = await odds_service.get_all_todays_games()

        synced = 0
        updated = 0

        for cat, sports_dict in categories_to_sync.items():
            for sport_key, events in sports_dict.items():
                for event in events:
                    external_id = event.get("id")
                    existing = db.query(SportsMatch).filter(
                        SportsMatch.external_id == external_id
                    ).first()

                    if existing:
                        existing.odds_data = event.get("bookmakers", [])
                        existing.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        match = SportsMatch(
                            external_id=external_id,
                            sport_key=sport_key,
                            sport_title=event.get("sport_title", sport_key.upper()),
                            home_team=event.get("home_team"),
                            away_team=event.get("away_team"),
                            commence_time=datetime.fromisoformat(
                                event.get("commence_time").replace('Z', '+00:00')
                            ),
                            status=MatchStatus.UPCOMING,
                            odds_data=event.get("bookmakers", [])
                        )
                        db.add(match)
                        synced += 1

        db.commit()

        # Clean up old matches (>7 days with no bets)
        cleanup_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        old_matches = db.query(SportsMatch).filter(
            SportsMatch.created_at < cleanup_cutoff
        ).all()

        cleaned_count = 0
        for match in old_matches:
            # Check if match has any bets
            has_bets = db.query(BetPick).filter(
                BetPick.match_id == match.id
            ).first() is not None

            if not has_bets:
                db.delete(match)
                cleaned_count += 1

        db.commit()

        # Update sync metadata
        sync_meta.last_sync_time = datetime.now(timezone.utc)
        sync_meta.sync_status = "success"
        sync_meta.games_synced = synced + updated
        sync_meta.error_message = None
        db.commit()

        return {
            "success": True,
            "new_matches": synced,
            "updated_matches": updated,
            "cleaned_matches": cleaned_count
        }

    except Exception as e:
        logger.error(f"Sync failed: {str(e)}", exc_info=True)
        db.rollback()

        # Mark sync as failed
        if sync_meta:
            sync_meta.sync_status = "failed"
            sync_meta.error_message = str(e)[:500]
            db.commit()

        raise HTTPException(500, f"Failed to sync: {str(e)}")


@router.delete("/bets/{bet_id}")
def cancel_bet(
    bet_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Cancel a pending bet and refund the stake.
    Only allowed while every game in the bet hasn't started yet.
    Admins can cancel any bet; users can only cancel their own.
    """
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if not bet:
        raise HTTPException(404, "Bet not found")

    # Check ownership (allow admin to cancel any bet)
    user = db.query(User).filter(User.id == user_id).first()
    is_user_admin = user and (
        user.role == "admin"
        or user.username in ["svidthekid"]
        or user.email in ["svidron.robert@gmail.com"]
    )
    if bet.user_id != user_id and not is_user_admin:
        raise HTTPException(403, "You can only cancel your own bets")

    if bet.status != BetStatus.PENDING:
        raise HTTPException(400, f"Cannot cancel a bet with status '{bet.status.value}'")

    # Block cancellation if any game has already started
    now = datetime.now(timezone.utc)
    for pick in bet.picks:
        match = db.query(SportsMatch).get(pick.match_id)
        if match:
            commence = match.commence_time
            if commence.tzinfo is None:
                commence = commence.replace(tzinfo=timezone.utc)
            if commence <= now:
                raise HTTPException(
                    400,
                    f"Cannot cancel — {match.away_team} @ {match.home_team} has already started"
                )

    # Mark cancelled
    bet.status = BetStatus.CANCELLED
    bet.settled_at = now
    bet.actual_payout = bet.stake  # refund

    for pick in bet.picks:
        pick.result = BetStatus.CANCELLED

    # Reverse leaderboard wagered amount so net_profit stays accurate
    sport_category_map = {
        "basketball": ["basketball_nba", "basketball_ncaab", "basketball_wnba", "basketball_euroleague"],
        "football": ["americanfootball_nfl", "americanfootball_ncaaf", "americanfootball_cfl", "australianfootball_afl"],
        "baseball": ["baseball_mlb", "baseball_kbo", "baseball_npb"],
        "hockey": ["icehockey_nhl", "icehockey_ahl", "icehockey_shl", "icehockey_allsvenskan", "icehockey_liiga"],
        "soccer": ["soccer_epl", "soccer_germany_bundesliga", "soccer_spain_la_liga",
                   "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_brazil_campeonato",
                   "soccer_uefa_champs_league", "soccer_uefa_europa_league"],
    }
    first_match = db.query(SportsMatch).get(bet.picks[0].match_id)
    sport_category = "other"
    if first_match:
        for cat, keys in sport_category_map.items():
            if first_match.sport_key in keys:
                sport_category = cat
                break

    lb = db.query(SportsLeaderboard).filter(
        SportsLeaderboard.user_id == bet.user_id,
        SportsLeaderboard.sport_category == sport_category
    ).first()
    if lb:
        lb.total_bets = max(0, lb.total_bets - 1)
        if bet.is_parlay:
            lb.total_parlays = max(0, lb.total_parlays - 1)
        lb.total_wagered = max(0, lb.total_wagered - bet.stake)
        lb.net_profit = lb.total_won - lb.total_wagered

    db.commit()
    return {"success": True, "bet_id": bet_id, "refunded": bet.stake}


@router.get("/admin/stats")
def admin_get_stats(
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin: Bet and match summary counts"""
    from sqlalchemy import func
    counts = db.query(Bet.status, func.count(Bet.id)).group_by(Bet.status).all()
    status_map = {str(s): c for s, c in counts}
    completed_matches = db.query(SportsMatch).filter(SportsMatch.status == MatchStatus.COMPLETED).count()
    return {
        "pending": status_map.get("pending", 0),
        "won": status_map.get("won", 0),
        "lost": status_map.get("lost", 0),
        "push": status_map.get("push", 0),
        "completed_matches": completed_matches,
    }


@router.get("/admin/bets")
def admin_get_bets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin: List all bets with pick details and username"""
    query = db.query(Bet).order_by(desc(Bet.placed_at))
    if status:
        query = query.filter(Bet.status == status)
    bets = query.limit(200).all()

    result = []
    for bet in bets:
        user = db.query(User).filter(User.id == bet.user_id).first()
        pick_responses = []
        for pick in bet.picks:
            match = db.query(SportsMatch).get(pick.match_id)
            pick_responses.append({
                "id": pick.id,
                "match_id": pick.match_id,
                "match_description": f"{match.away_team} @ {match.home_team}" if match else "Unknown",
                "bet_type": pick.bet_type.value,
                "selection": pick.selection.value,
                "odds": pick.odds,
                "point": pick.point,
                "result": pick.result.value if pick.result else None,
            })
        result.append({
            "id": bet.id,
            "user_id": bet.user_id,
            "username": user.username if user else str(bet.user_id),
            "is_parlay": bet.is_parlay,
            "total_picks": bet.total_picks,
            "stake": bet.stake,
            "potential_payout": bet.potential_payout,
            "actual_payout": bet.actual_payout,
            "status": bet.status.value,
            "placed_at": bet.placed_at.isoformat(),
            "settled_at": bet.settled_at.isoformat() if bet.settled_at else None,
            "picks": pick_responses,
        })
    return {"bets": result, "total": len(result)}


@router.get("/admin/matches")
def admin_get_matches(
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin: List all matches in DB (most recent first)"""
    matches = db.query(SportsMatch).order_by(desc(SportsMatch.commence_time)).limit(100).all()
    return {
        "matches": [
            {
                "id": m.id,
                "external_id": m.external_id,
                "sport_key": m.sport_key,
                "sport_title": m.sport_title,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "commence_time": m.commence_time.isoformat(),
                "status": m.status.value,
                "home_score": m.home_score,
                "away_score": m.away_score,
            }
            for m in matches
        ]
    }


@router.post("/admin/bets/{bet_id}/force-settle")
def admin_force_settle_bet(
    bet_id: int,
    outcome: str,  # "won" or "lost"
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin: Force a pending bet to won or lost regardless of game state."""
    if outcome not in ("won", "lost"):
        raise HTTPException(400, "outcome must be 'won' or 'lost'")

    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if not bet:
        raise HTTPException(404, "Bet not found")
    if bet.status != BetStatus.PENDING:
        raise HTTPException(400, f"Bet is already '{bet.status.value}'")

    now = datetime.now(timezone.utc)
    if outcome == "won":
        bet.status = BetStatus.WON
        bet.actual_payout = bet.potential_payout
        for pick in bet.picks:
            pick.result = BetStatus.WON
    else:
        bet.status = BetStatus.LOST
        bet.actual_payout = 0
        for pick in bet.picks:
            pick.result = BetStatus.LOST

    bet.settled_at = now

    # Update leaderboard
    sport_category_map = {
        "basketball": ["basketball_nba", "basketball_ncaab", "basketball_wnba", "basketball_euroleague"],
        "football": ["americanfootball_nfl", "americanfootball_ncaaf", "americanfootball_cfl", "australianfootball_afl"],
        "baseball": ["baseball_mlb", "baseball_kbo", "baseball_npb"],
        "hockey": ["icehockey_nhl", "icehockey_ahl", "icehockey_shl", "icehockey_allsvenskan", "icehockey_liiga"],
        "soccer": ["soccer_epl", "soccer_germany_bundesliga", "soccer_spain_la_liga",
                   "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_brazil_campeonato",
                   "soccer_uefa_champs_league", "soccer_uefa_europa_league"],
    }
    first_match = db.query(SportsMatch).get(bet.picks[0].match_id) if bet.picks else None
    sport_category = "other"
    if first_match:
        for cat, keys in sport_category_map.items():
            if first_match.sport_key in keys:
                sport_category = cat
                break

    update_leaderboard(db, bet.user_id, sport_category, bet)
    db.commit()

    return {
        "success": True,
        "bet_id": bet_id,
        "outcome": outcome,
        "payout": bet.actual_payout,
    }


@router.post("/admin/settle-bets")
def admin_settle_bets(
    db: Session = Depends(get_db),
    _admin: bool = Depends(is_admin)
):
    """Admin: Manually trigger bet settlement by fetching scores from The Odds API"""
    result = settle_completed_matches(db)
    return {"success": True, **result}


@router.post("/admin/update-result/{match_id}")
def update_match_result(
    match_id: int,
    home_score: int,
    away_score: int,
    db: Session = Depends(get_db)
):
    """Admin: Update match result and settle bets"""
    match = db.query(SportsMatch).get(match_id)
    if not match:
        raise HTTPException(404, "Match not found")

    match.home_score = home_score
    match.away_score = away_score
    match.status = MatchStatus.COMPLETED
    match.completed_at = datetime.now(timezone.utc)

    # Get all picks for this match
    picks = db.query(BetPick).filter(BetPick.match_id == match_id).all()
    settled_bets = set()

    for pick in picks:
        pick.result = determine_pick_result(pick, match)
        settled_bets.add(pick.bet_id)

    # Evaluate each bet
    for bet_id in settled_bets:
        bet = db.query(Bet).get(bet_id)
        all_won = all(p.result == BetStatus.WON for p in bet.picks)
        any_lost = any(p.result == BetStatus.LOST for p in bet.picks)
        all_push = all(p.result == BetStatus.PUSH for p in bet.picks)

        if any_lost:
            bet.status = BetStatus.LOST
            bet.actual_payout = 0
        elif all_won:
            bet.status = BetStatus.WON
            bet.actual_payout = bet.potential_payout
        elif all_push:
            bet.status = BetStatus.PUSH
            bet.actual_payout = bet.stake

        if bet.status != BetStatus.PENDING:
            bet.settled_at = datetime.now(timezone.utc)

            # Determine sport category
            match_obj = db.query(SportsMatch).get(bet.picks[0].match_id)
            sport_key = match_obj.sport_key

            category_map = {
                "basketball": ["basketball_nba", "basketball_ncaab", "basketball_wnba"],
                "football": ["americanfootball_nfl", "americanfootball_ncaaf", "americanfootball_cfl"],
                "baseball": ["baseball_mlb", "baseball_kbo", "baseball_npb"],
                "hockey": ["icehockey_nhl", "icehockey_ahl", "icehockey_shl"],
                "soccer": ["soccer_epl", "soccer_germany_bundesliga", "soccer_spain_la_liga"]
            }

            sport_category = "other"
            for cat, keys in category_map.items():
                if sport_key in keys:
                    sport_category = cat
                    break

            update_leaderboard(db, bet.user_id, sport_category, bet)

    db.commit()

    return {"success": True, "picks_settled": len(picks), "bets_evaluated": len(settled_bets)}
