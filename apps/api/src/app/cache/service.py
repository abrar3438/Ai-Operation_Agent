from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger("app.cache")

# Schema / data version for cache keys to prevent stale object deserialization across migrations
CACHE_SCHEMA_VERSION = "v1"

# Explicitly approved deterministic read-only tools eligible for caching
ELIGIBLE_READ_ONLY_TOOLS = {"get_customer", "get_order", "search_database", "search_documents"}


class CacheService:
    def __init__(self, redis_client: Redis | None = None) -> None:
        self.settings = get_settings()
        self._redis = redis_client

    def _get_client(self) -> Redis | None:
        if not self.settings.cache_enabled or not self.settings.redis_enabled:
            return None
        if self._redis is not None:
            return self._redis
        try:
            from app.cache.redis_client import create_redis_client

            self._redis = create_redis_client(self.settings.redis_url)
            return self._redis
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to initialize Redis client for caching: %s", e)
            return None

    def make_key(self, tool_name: str, params: dict[str, Any]) -> str:
        """Construct a namespaced, deterministic cache key.

        Format: aiops:cache:{version}:{tool_name}:{hashed_params}
        Includes schema version and sorted JSON parameters to guarantee uniqueness.
        Never includes API keys or sensitive auth tokens.
        """
        sanitized = {
            k: v for k, v in params.items() if k not in {"api_key", "password", "secret", "token"}
        }
        serialized = json.dumps(sanitized, sort_keys=True, default=str)
        param_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]
        return f"aiops:cache:{CACHE_SCHEMA_VERSION}:{tool_name}:{param_hash}"

    def get(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if tool_name not in ELIGIBLE_READ_ONLY_TOOLS:
            return None
        client = self._get_client()
        if client is None:
            return None
        key = self.make_key(tool_name, params)
        try:
            raw = client.get(key)
            if raw is not None:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                parsed = json.loads(str(raw))
                if isinstance(parsed, dict):
                    return parsed
        except (RedisError, TimeoutError, json.JSONDecodeError) as e:
            logger.warning("Cache GET error for key %s (degrading gracefully): %s", key, e)
        except Exception as e:  # noqa: BLE001
            logger.warning("Unexpected cache GET error: %s", e)
        return None

    def set(
        self,
        tool_name: str,
        params: dict[str, Any],
        value: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache approved read-only tool results.

        Action tools (create_ticket, send_report) and errors/failures are NEVER cached.
        """
        if tool_name not in ELIGIBLE_READ_ONLY_TOOLS:
            return
        # Never cache tool failures or errors as success
        if value.get("status") and value.get("status") != "ok":
            return
        client = self._get_client()
        if client is None:
            return
        key = self.make_key(tool_name, params)
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.cache_default_ttl_seconds
        try:
            payload = json.dumps(value, default=str)
            client.setex(key, ttl, payload)
        except (RedisError, TimeoutError, TypeError) as e:
            logger.warning("Cache SET error for key %s (degrading gracefully): %s", key, e)
        except Exception as e:  # noqa: BLE001
            logger.warning("Unexpected cache SET error: %s", e)
