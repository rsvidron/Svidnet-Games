"""
The Odds API Integration Service
Fetches live sports odds for betting predictions
"""
import httpx
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.core.config import settings

# Try to import redis, but make it optional
try:
    from app.core.redis import redis_client
except ImportError:
    redis_client = None
    logging.warning("Redis not available - caching disabled for odds service")

logger = logging.getLogger(__name__)


class OddsAPIService:
    """Service for interacting with The Odds API"""

    def __init__(self):
        self.base_url = settings.ODDS_API_BASE_URL
        self.api_key = settings.ODDS_API_KEY
        self.cache_ttl = settings.ODDS_CACHE_TTL_SECONDS
        self.timeout = 10.0

        # Sport mapping: category -> API sport keys
        self.sport_categories = {
            "football": [
                "americanfootball_nfl",
                "americanfootball_ncaaf",
                "americanfootball_cfl",
                "australianfootball_afl"
            ],
            "basketball": [
                "basketball_nba",
                "basketball_ncaab",
                "basketball_wnba",
                "basketball_euroleague"
            ],
            "baseball": [
                "baseball_mlb",
                "baseball_kbo",
                "baseball_npb"
            ],
            "hockey": [
                "icehockey_nhl",
                "icehockey_ahl",
                "icehockey_shl",
                "icehockey_allsvenskan",
                "icehockey_liiga"
            ],
            "soccer": [
                "soccer_epl",
                "soccer_germany_bundesliga",
                "soccer_spain_la_liga",
                "soccer_italy_serie_a",
                "soccer_france_ligue_one",
                "soccer_brazil_campeonato",
                "soccer_uefa_champs_league",
                "soccer_uefa_europa_league"
            ]
        }

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make HTTP request to The Odds API with error handling"""
        url = f"{self.base_url}/{endpoint}"

        # Add API key to params
        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Odds API HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Odds API request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Odds API: {str(e)}")
            return None

    async def get_available_sports(self) -> List[Dict]:
        """Fetch list of available sports from the API"""
        cache_key = "odds:available_sports"

        # Try cache first
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return cached

        sports = await self._make_request("sports")

        if sports and redis_client:
            # Cache for 1 hour (sports list doesn't change often)
            await redis_client.set(cache_key, sports, ex=3600)

        return sports or []

    async def get_odds(
        self,
        sport: str,
        regions: str = "us",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "american"
    ) -> List[Dict]:
        """
        Fetch odds for a specific sport

        Args:
            sport: Sport key (e.g., 'basketball_nba')
            regions: Betting regions (default: 'us')
            markets: Betting markets (h2h=moneyline, spreads, totals=over/under)
            odds_format: 'american', 'decimal', or 'fractional'

        Returns:
            List of events with odds
        """
        cache_key = f"odds:{sport}:{markets}"

        # Try cache first
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {sport} odds")
                return cached

        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": "iso"
        }

        odds_data = await self._make_request(f"sports/{sport}/odds", params)

        if odds_data and redis_client:
            # Cache for configured TTL (default 5 minutes)
            await redis_client.set(cache_key, odds_data, ex=self.cache_ttl)
            logger.info(f"Cached {sport} odds for {self.cache_ttl}s")

        return odds_data or []

    async def get_odds_by_category(
        self,
        category: str,
        markets: str = "h2h,spreads,totals"
    ) -> Dict[str, List[Dict]]:
        """
        Fetch odds for all sports in a category (e.g., 'basketball', 'football')

        Returns:
            Dict mapping sport key to events list
        """
        if category not in self.sport_categories:
            logger.warning(f"Unknown sport category: {category}")
            return {}

        sports_in_category = self.sport_categories[category]
        results = {}

        for sport in sports_in_category:
            odds = await self.get_odds(sport, markets=markets)
            if odds:
                results[sport] = odds

        return results

    async def get_all_todays_games(self) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Fetch all games happening today across all categories

        Returns:
            {
                'football': {'americanfootball_nfl': [events...], ...},
                'basketball': {'basketball_nba': [events...], ...},
                ...
            }
        """
        all_games = {}

        for category in self.sport_categories.keys():
            category_odds = await self.get_odds_by_category(category)
            if category_odds:
                all_games[category] = category_odds

        return all_games

    async def get_event_odds(self, sport: str, event_id: str) -> Optional[Dict]:
        """
        Fetch odds for a specific event

        Args:
            sport: Sport key
            event_id: Event ID from The Odds API

        Returns:
            Event with detailed odds or None
        """
        cache_key = f"odds:event:{event_id}"

        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return cached

        params = {
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "dateFormat": "iso"
        }

        event_data = await self._make_request(f"sports/{sport}/odds", params)

        if event_data:
            # Find specific event
            event = next((e for e in event_data if e.get("id") == event_id), None)

            if event and redis_client:
                await redis_client.set(cache_key, event, ex=self.cache_ttl)

            return event

        return None

    def parse_odds_for_display(self, event: Dict) -> Dict:
        """
        Parse raw odds data into user-friendly format

        Returns:
            {
                'event_id': str,
                'sport': str,
                'commence_time': str (ISO),
                'home_team': str,
                'away_team': str,
                'moneyline': {'home': int, 'away': int, 'draw': int|None},
                'spreads': {'home': {'point': float, 'odds': int}, 'away': {...}},
                'totals': {'over': {'point': float, 'odds': int}, 'under': {...}}
            }
        """
        parsed = {
            "event_id": event.get("id"),
            "sport": event.get("sport_key"),
            "commence_time": event.get("commence_time"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "moneyline": {},
            "spreads": {},
            "totals": {}
        }

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return parsed

        # Use first bookmaker (usually most popular)
        bookmaker = bookmakers[0]
        markets = bookmaker.get("markets", [])

        for market in markets:
            market_key = market.get("key")
            outcomes = market.get("outcomes", [])

            if market_key == "h2h":  # Moneyline
                for outcome in outcomes:
                    team = outcome.get("name")
                    price = outcome.get("price")

                    if team == parsed["home_team"]:
                        parsed["moneyline"]["home"] = price
                    elif team == parsed["away_team"]:
                        parsed["moneyline"]["away"] = price
                    else:  # Draw (for soccer)
                        parsed["moneyline"]["draw"] = price

            elif market_key == "spreads":
                for outcome in outcomes:
                    team = outcome.get("name")
                    point = outcome.get("point")
                    price = outcome.get("price")

                    if team == parsed["home_team"]:
                        parsed["spreads"]["home"] = {"point": point, "odds": price}
                    elif team == parsed["away_team"]:
                        parsed["spreads"]["away"] = {"point": point, "odds": price}

            elif market_key == "totals":
                for outcome in outcomes:
                    name = outcome.get("name")
                    point = outcome.get("point")
                    price = outcome.get("price")

                    if name == "Over":
                        parsed["totals"]["over"] = {"point": point, "odds": price}
                    elif name == "Under":
                        parsed["totals"]["under"] = {"point": point, "odds": price}

        return parsed

    async def check_api_quota(self) -> Dict:
        """
        Check remaining API quota
        The Odds API includes quota info in response headers
        """
        # Make a minimal request to check quota
        sports = await self.get_available_sports()

        # Note: In production, you'd extract quota from response headers
        # For now, return basic info
        return {
            "sports_available": len(sports) if sports else 0,
            "status": "ok" if sports else "error"
        }


# Create global instance
odds_service = OddsAPIService()
