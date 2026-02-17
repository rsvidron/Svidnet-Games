"""
Test script for Sportsbook functionality
Tests single bet and 3-leg parlay
"""
import sys
import os
sys.path.insert(0, 'backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models.sports import SportsMatch, Bet, BetPick, BetStatus, MatchStatus, BetType, BetSelection
from models.user import User, UserProfile
from datetime import datetime, timezone, timedelta
import json

# Create test database
engine = create_engine('sqlite:///test_sportsbook.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 60)
print("SPORTSBOOK TEST SUITE")
print("=" * 60)

# 1. Create test user
user = db.query(User).filter(User.username == "test_bettor").first()
if not user:
    user = User(
        username="test_bettor",
        email="bettor@test.com",
        hashed_password="test",
        role="user"
    )
    db.add(user)
    db.commit()
    print(f"✓ Created test user: {user.username} (ID: {user.id})")
else:
    print(f"✓ Using existing user: {user.username} (ID: {user.id})")

# 2. Create test games (simulate upcoming NBA games)
games_data = [
    {
        "external_id": "test_game_1",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "moneyline_home": -150,
        "moneyline_away": 130,
        "spread_home": -3.5,
        "spread_away": 3.5,
        "spread_odds": -110,
        "total": 225.5,
        "total_odds": -110
    },
    {
        "external_id": "test_game_2",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "home_team": "Golden State Warriors",
        "away_team": "Miami Heat",
        "moneyline_home": -200,
        "moneyline_away": 170,
        "spread_home": -5.5,
        "spread_away": 5.5,
        "spread_odds": -110,
        "total": 218.5,
        "total_odds": -110
    },
    {
        "external_id": "test_game_3",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "home_team": "Milwaukee Bucks",
        "away_team": "Phoenix Suns",
        "moneyline_home": -180,
        "moneyline_away": 155,
        "spread_home": -4.5,
        "spread_away": 4.5,
        "spread_odds": -110,
        "total": 230.5,
        "total_odds": -110
    }
]

matches = []
for game_data in games_data:
    match = db.query(SportsMatch).filter(SportsMatch.external_id == game_data["external_id"]).first()
    if not match:
        match = SportsMatch(
            external_id=game_data["external_id"],
            sport_key=game_data["sport_key"],
            sport_title=game_data["sport_title"],
            home_team=game_data["home_team"],
            away_team=game_data["away_team"],
            commence_time=datetime.now(timezone.utc) + timedelta(hours=2),  # Game in 2 hours
            status=MatchStatus.UPCOMING,
            odds_data={}
        )
        db.add(match)
        db.commit()
        print(f"✓ Created game: {match.away_team} @ {match.home_team}")
    else:
        print(f"✓ Using existing game: {match.away_team} @ {match.home_team}")
    matches.append((match, game_data))

print()
print("=" * 60)
print("TEST 1: SINGLE BET (Moneyline)")
print("=" * 60)

# Test 1: Single Bet - Lakers Moneyline
match1, game1_data = matches[0]

bet1 = Bet(
    user_id=user.id,
    is_parlay=False,
    total_picks=1,
    stake=10,
    status=BetStatus.PENDING
)
db.add(bet1)
db.flush()

pick1 = BetPick(
    bet_id=bet1.id,
    match_id=match1.id,
    bet_type=BetType.MONEYLINE,
    selection=BetSelection.HOME,  # Lakers
    odds=game1_data["moneyline_home"]
)
db.add(pick1)

# Calculate payout
american_odds = pick1.odds
if american_odds > 0:
    decimal_odds = (american_odds / 100) + 1
else:
    decimal_odds = (100 / abs(american_odds)) + 1

bet1.potential_payout = round(bet1.stake * decimal_odds, 2)
db.commit()

print(f"📊 Single Bet Details:")
print(f"   Match: {match1.away_team} @ {match1.home_team}")
print(f"   Bet Type: Moneyline")
print(f"   Selection: {match1.home_team} (HOME)")
print(f"   Odds: {pick1.odds} (American)")
print(f"   Stake: {bet1.stake} points")
print(f"   Potential Payout: {bet1.potential_payout} points")
print(f"   Status: {bet1.status.value}")
print(f"   Bet ID: {bet1.id}")

print()
print("=" * 60)
print("TEST 2: 3-LEG PARLAY")
print("=" * 60)

# Test 2: 3-Leg Parlay
# Pick 1: Lakers -3.5 (Spread)
# Pick 2: Warriors ML (Moneyline)
# Pick 3: Bucks vs Suns Over 230.5 (Total)

parlay_picks_data = [
    {
        "match": matches[0],  # Lakers vs Celtics
        "bet_type": BetType.SPREAD,
        "selection": BetSelection.HOME,  # Lakers -3.5
        "odds": -110,
        "point": -3.5,
        "description": "Lakers -3.5"
    },
    {
        "match": matches[1],  # Warriors vs Heat
        "bet_type": BetType.MONEYLINE,
        "selection": BetSelection.HOME,  # Warriors ML
        "odds": -200,
        "point": None,
        "description": "Warriors ML"
    },
    {
        "match": matches[2],  # Bucks vs Suns
        "bet_type": BetType.TOTAL,
        "selection": BetSelection.OVER,  # Over 230.5
        "odds": -110,
        "point": 230.5,
        "description": "Over 230.5"
    }
]

parlay_bet = Bet(
    user_id=user.id,
    is_parlay=True,
    total_picks=3,
    stake=10,
    status=BetStatus.PENDING
)
db.add(parlay_bet)
db.flush()

print(f"🎯 3-Leg Parlay Details:")
print(f"   Stake: {parlay_bet.stake} points")
print()

total_decimal_odds = 1.0
for i, pick_data in enumerate(parlay_picks_data, 1):
    match, game_data = pick_data["match"]

    pick = BetPick(
        bet_id=parlay_bet.id,
        match_id=match.id,
        bet_type=pick_data["bet_type"],
        selection=pick_data["selection"],
        odds=pick_data["odds"],
        point=pick_data["point"]
    )
    db.add(pick)

    # Convert to decimal odds
    american_odds = pick.odds
    if american_odds > 0:
        decimal_odds = (american_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(american_odds)) + 1

    total_decimal_odds *= decimal_odds

    print(f"   Leg {i}: {match.away_team} @ {match.home_team}")
    print(f"          {pick_data['description']} at {pick.odds}")
    print(f"          Decimal odds: {decimal_odds:.3f}")
    print()

parlay_bet.potential_payout = round(parlay_bet.stake * total_decimal_odds, 2)
db.commit()

print(f"   Combined Decimal Odds: {total_decimal_odds:.3f}x")
print(f"   Potential Payout: {parlay_bet.potential_payout} points")
print(f"   Potential Profit: {parlay_bet.potential_payout - parlay_bet.stake} points")
print(f"   Status: {parlay_bet.status.value}")
print(f"   Parlay ID: {parlay_bet.id}")

print()
print("=" * 60)
print("TEST 3: SIMULATE GAME RESULTS & BET SETTLEMENT")
print("=" * 60)

# Simulate game 1 result: Lakers win 110-105 (covers -3.5 spread)
match1.home_score = 110
match1.away_score = 105
match1.status = MatchStatus.COMPLETED
match1.completed_at = datetime.now(timezone.utc)

# Simulate game 2 result: Warriors win 115-108
matches[1][0].home_score = 115
matches[1][0].away_score = 108
matches[1][0].status = MatchStatus.COMPLETED
matches[1][0].completed_at = datetime.now(timezone.utc)

# Simulate game 3 result: Total 235 (Over 230.5 hits)
matches[2][0].home_score = 120
matches[2][0].away_score = 115
matches[2][0].status = MatchStatus.COMPLETED
matches[2][0].completed_at = datetime.now(timezone.utc)

db.commit()

# Settle single bet
print("🎲 Game 1 Result: Lakers 110, Celtics 105")
print(f"   Lakers ML: ✅ WIN (Lakers won)")
pick1.result = BetStatus.WON
bet1.status = BetStatus.WON
bet1.actual_payout = bet1.potential_payout
bet1.settled_at = datetime.now(timezone.utc)
db.commit()

print(f"   Single Bet Status: {bet1.status.value}")
print(f"   Payout: {bet1.actual_payout} points")
print()

# Settle parlay picks
print("🎲 Parlay Results:")
parlay_picks = db.query(BetPick).filter(BetPick.bet_id == parlay_bet.id).all()

for i, pick in enumerate(parlay_picks, 1):
    match = db.query(SportsMatch).get(pick.match_id)

    # Determine result
    if pick.bet_type == BetType.SPREAD:
        home_with_spread = match.home_score + pick.point
        if pick.selection == BetSelection.HOME:
            pick.result = BetStatus.WON if home_with_spread > match.away_score else BetStatus.LOST
        else:
            pick.result = BetStatus.WON if home_with_spread < match.away_score else BetStatus.LOST

        print(f"   Leg {i}: {match.home_team} {match.home_score}, {match.away_team} {match.away_score}")
        print(f"          {match.home_team} {pick.point} → With spread: {home_with_spread}")
        print(f"          Result: {'✅ WIN' if pick.result == BetStatus.WON else '❌ LOSS'}")

    elif pick.bet_type == BetType.MONEYLINE:
        if pick.selection == BetSelection.HOME:
            pick.result = BetStatus.WON if match.home_score > match.away_score else BetStatus.LOST
        else:
            pick.result = BetStatus.WON if match.away_score > match.home_score else BetStatus.LOST

        print(f"   Leg {i}: {match.home_team} {match.home_score}, {match.away_team} {match.away_score}")
        print(f"          {match.home_team} ML → Result: {'✅ WIN' if pick.result == BetStatus.WON else '❌ LOSS'}")

    elif pick.bet_type == BetType.TOTAL:
        total_points = match.home_score + match.away_score
        if pick.selection == BetSelection.OVER:
            pick.result = BetStatus.WON if total_points > pick.point else BetStatus.LOST
        else:
            pick.result = BetStatus.WON if total_points < pick.point else BetStatus.LOST

        print(f"   Leg {i}: {match.home_team} {match.home_score}, {match.away_team} {match.away_score}")
        print(f"          Total: {total_points} vs Line: {pick.point}")
        print(f"          Over {pick.point} → Result: {'✅ WIN' if pick.result == BetStatus.WON else '❌ LOSS'}")

    print()

# Check if all parlay picks won
all_won = all(p.result == BetStatus.WON for p in parlay_picks)
any_lost = any(p.result == BetStatus.LOST for p in parlay_picks)

if all_won:
    parlay_bet.status = BetStatus.WON
    parlay_bet.actual_payout = parlay_bet.potential_payout
    print(f"🎊 PARLAY RESULT: ✅ WON!")
    print(f"   All 3 legs hit!")
    print(f"   Payout: {parlay_bet.actual_payout} points")
    print(f"   Profit: {parlay_bet.actual_payout - parlay_bet.stake} points")
elif any_lost:
    parlay_bet.status = BetStatus.LOST
    parlay_bet.actual_payout = 0
    print(f"💔 PARLAY RESULT: ❌ LOST")
    print(f"   At least one leg missed")
    print(f"   Payout: 0 points")

parlay_bet.settled_at = datetime.now(timezone.utc)
db.commit()

print()
print("=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

all_bets = db.query(Bet).filter(Bet.user_id == user.id).all()
total_wagered = sum(b.stake for b in all_bets)
total_won = sum(b.actual_payout for b in all_bets)
net_profit = total_won - total_wagered

print(f"User: {user.username}")
print(f"Total Bets Placed: {len(all_bets)}")
print(f"  - Single Bets: {sum(1 for b in all_bets if not b.is_parlay)}")
print(f"  - Parlays: {sum(1 for b in all_bets if b.is_parlay)}")
print(f"Total Wagered: {total_wagered} points")
print(f"Total Won: {total_won} points")
print(f"Net Profit: {net_profit:+.2f} points")

won_bets = [b for b in all_bets if b.status == BetStatus.WON]
lost_bets = [b for b in all_bets if b.status == BetStatus.LOST]
print(f"Record: {len(won_bets)}W - {len(lost_bets)}L")

print()
print("✅ All tests completed successfully!")
print()

# Cleanup
db.close()
