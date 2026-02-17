"""
Redis connection and utilities
Used for caching, sessions, and real-time game state
"""
import redis.asyncio as aioredis
from typing import Optional, Any
import json
from .config import settings


class RedisClient:
    """Async Redis client wrapper"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        if not self.redis:
            return None
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set key-value pair

        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if dict/list)
            expire: Optional expiration in seconds
        """
        if not self.redis:
            return False

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if expire:
            return await self.redis.setex(key, expire, value)
        else:
            return await self.redis.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete a key"""
        if not self.redis:
            return False
        return await self.redis.delete(key) > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0

    async def increment(self, key: str) -> int:
        """Increment a counter"""
        if not self.redis:
            return 0
        return await self.redis.incr(key)

    async def add_to_set(self, key: str, *values) -> int:
        """Add values to a set"""
        if not self.redis:
            return 0
        return await self.redis.sadd(key, *values)

    async def get_set_members(self, key: str) -> set:
        """Get all members of a set"""
        if not self.redis:
            return set()
        return await self.redis.smembers(key)

    async def remove_from_set(self, key: str, *values) -> int:
        """Remove values from a set"""
        if not self.redis:
            return 0
        return await self.redis.srem(key, *values)

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to a channel"""
        if not self.redis:
            return 0
        return await self.redis.publish(channel, message)

    async def add_to_sorted_set(
        self,
        key: str,
        score: float,
        member: str
    ) -> int:
        """Add member to sorted set with score"""
        if not self.redis:
            return 0
        return await self.redis.zadd(key, {member: score})

    async def get_sorted_set_range(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        reverse: bool = True
    ) -> list:
        """
        Get range from sorted set

        Args:
            key: Redis key
            start: Start index
            end: End index (-1 for all)
            reverse: If True, return in descending order
        """
        if not self.redis:
            return []

        if reverse:
            return await self.redis.zrevrange(
                key,
                start,
                end,
                withscores=True
            )
        else:
            return await self.redis.zrange(
                key,
                start,
                end,
                withscores=True
            )


# Global Redis client instance
redis_client = RedisClient()


# Helper functions for game-specific caching
async def cache_game_session(session_id: int, data: dict, ttl: int = 3600):
    """Cache game session data"""
    await redis_client.set(f"game_session:{session_id}", data, expire=ttl)


async def get_game_session(session_id: int) -> Optional[dict]:
    """Retrieve cached game session"""
    return await redis_client.get(f"game_session:{session_id}")


async def cache_leaderboard(
    leaderboard_type: str,
    entries: list,
    ttl: int = 300
):
    """Cache leaderboard entries"""
    await redis_client.set(
        f"leaderboard:{leaderboard_type}",
        entries,
        expire=ttl
    )


async def get_cached_leaderboard(leaderboard_type: str) -> Optional[list]:
    """Retrieve cached leaderboard"""
    return await redis_client.get(f"leaderboard:{leaderboard_type}")


async def add_active_room(room_code: str, room_data: dict):
    """Add active game room to cache"""
    await redis_client.set(f"room:{room_code}", room_data, expire=7200)


async def get_active_room(room_code: str) -> Optional[dict]:
    """Get active room data"""
    return await redis_client.get(f"room:{room_code}")


async def remove_active_room(room_code: str):
    """Remove room from cache"""
    await redis_client.delete(f"room:{room_code}")
