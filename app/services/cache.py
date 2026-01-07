"""
Redis Cache Service
Provides caching utilities for Quimbi API responses.
"""
import redis.asyncio as aioredis
from app.core.config import settings
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Async Redis cache wrapper."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.enabled = True

    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.enabled = False

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.enabled or not self.redis:
            return None

        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def setex(self, key: str, ttl: int, value: str):
        """Set value with expiration (in seconds)."""
        if not self.enabled or not self.redis:
            return

        try:
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis setex error: {e}")

    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.enabled or not self.redis:
            return

        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()


# Global cache instance
redis_client = RedisCache()
