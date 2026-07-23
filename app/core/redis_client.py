"""Lazy Redis client for pub/sub and Celery coordination."""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import settings

CHANNEL_PRICES = "quantai:prices"
CHANNEL_NOTIFICATIONS = "quantai:notifications"
CHANNEL_SYSTEM = "quantai:system"


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def publish_json(channel: str, payload: str) -> None:
    try:
        get_redis().publish(channel, payload)
    except redis.RedisError:
        # Dev environments may run without Redis; REST still works.
        pass
