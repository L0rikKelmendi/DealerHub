"""Redis-backed cache with JSON (de)serialisation and pattern invalidation."""

import functools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("dealerhub.cache")


class RedisCache:
    """Thin async wrapper around redis-py used by the service layer."""

    def __init__(self, url: str):
        self._redis: aioredis.Redis = aioredis.from_url(url, decode_responses=True)

    @property
    def redis(self) -> aioredis.Redis:
        return self._redis

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:  # noqa: BLE001 - cache must never crash the app
            return False

    # --- basic operations ------------------------------------------------ #
    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
        except Exception:  # noqa: BLE001
            return None
        return json.loads(raw) if raw is not None else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:  # noqa: BLE001
            logger.warning("cache SET failed for %s", key)

    async def delete(self, *keys: str) -> None:
        try:
            await self._redis.delete(*keys)
        except Exception:  # noqa: BLE001
            logger.warning("cache DELETE failed for %s", keys)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete every key matching a glob pattern (vehicle:list:* etc.)."""
        try:
            keys = [k async for k in self._redis.scan_iter(match=pattern)]
            if keys:
                await self._redis.delete(*keys)
            return len(keys)
        except Exception:  # noqa: BLE001
            logger.warning("cache DELETE_PATTERN failed for %s", pattern)
            return 0

    async def flush(self) -> None:
        await self._redis.flushdb()

    async def close(self) -> None:
        await self._redis.aclose()


_cache: RedisCache | None = None


def get_cache() -> RedisCache:
    """Lazy singleton so tests can replace the URL before first use."""
    global _cache
    if _cache is None:
        _cache = RedisCache(settings.REDIS_URL)
    return _cache


def reset_cache() -> None:
    """Drop the singleton (used by tests to point the cache elsewhere)."""
    global _cache
    _cache = None


def cached(
    key_prefix: str,
    ttl: int | None = None,
    invalidate_patterns: tuple[str, ...] = (),
) -> Callable:
    """Decorator that memoises an async service method in Redis.

    The wrapped function receives ``self`` and its first positional argument
    is used for key building via ``str()`` (typically the tenant/company id).
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            key = f"{key_prefix}:{self.company_id}:{args}:{sorted(kwargs.items())}"
            hit = await cache.get_json(key)
            if hit is not None:
                logger.debug("cache HIT %s", key)
                return hit
            result = await func(self, *args, **kwargs)
            await cache.set_json(key, result, ttl=ttl or settings.CACHE_TTL_SECONDS)
            return result

        wrapper._cache_key_prefix = key_prefix  # type: ignore[attr-defined]
        wrapper._invalidate_patterns = invalidate_patterns  # type: ignore[attr-defined]
        return wrapper

    return decorator
