from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError

from app.config import get_settings


def create_redis_client(url: str | None = None) -> Redis:
    redis_url = url or get_settings().redis_url
    return Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)


def ping_ready(client: Redis | None = None) -> bool:
    target = client or create_redis_client()
    try:
        return bool(target.ping())
    except RedisError:
        return False
    except Exception:  # noqa: BLE001 - readiness probe must never raise
        return False
