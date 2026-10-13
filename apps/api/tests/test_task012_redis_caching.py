from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from redis import Redis  # noqa: E402
from redis.exceptions import RedisError  # noqa: E402

from app.cache.service import (  # noqa: E402
    ELIGIBLE_READ_ONLY_TOOLS,
    CacheService,
)
from app.models.contracts import ToolCallStatus  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


class FakeRedisClient(Redis):
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl_store: dict[str, int] = {}
        self.fail_next = False

    def get(self, name: str) -> str | None:
        if self.fail_next:
            raise RedisError("Simulated Redis outage")
        return self.store.get(name)

    def setex(self, name: str, time: int, value: str) -> bool:
        if self.fail_next:
            raise RedisError("Simulated Redis outage")
        self.store[name] = value
        self.ttl_store[name] = time
        return True

    def ping(self) -> bool:
        if self.fail_next:
            raise RedisError("Simulated Redis outage")
        return True


def test_cache_key_construction_and_versioning() -> None:
    service = CacheService()
    key1 = service.make_key("get_customer", {"customer_id": "CUST-1001"})
    key2 = service.make_key("get_customer", {"customer_id": "CUST-1002"})
    key3 = service.make_key("get_customer", {"customer_id": "CUST-1001"})

    assert "aiops:cache:v1:get_customer:" in key1
    assert key1 != key2
    assert key1 == key3


def test_eligible_tools_boundaries() -> None:
    assert "get_customer" in ELIGIBLE_READ_ONLY_TOOLS
    assert "get_order" in ELIGIBLE_READ_ONLY_TOOLS
    assert "create_ticket" not in ELIGIBLE_READ_ONLY_TOOLS
    assert "send_report" not in ELIGIBLE_READ_ONLY_TOOLS


def test_cache_hit_miss_and_expiration() -> None:
    fake_redis = FakeRedisClient()
    service = CacheService(redis_client=fake_redis)  # type: ignore[arg-type]

    params = {"customer_id": "CUST-1001"}
    assert service.get("get_customer", params) is None

    val = {
        "status": "ok",
        "result": {"customer_id": "CUST-1001", "display_name": "Test"},
    }
    service.set("get_customer", params, val, ttl_seconds=60)

    cached = service.get("get_customer", params)
    assert cached is not None
    assert cached["result"]["display_name"] == "Test"


def test_cache_outage_degrades_gracefully() -> None:
    fake_redis = FakeRedisClient()
    fake_redis.fail_next = True
    service = CacheService(redis_client=fake_redis)  # type: ignore[arg-type]

    assert service.get("get_customer", {"customer_id": "CUST-1001"}) is None
    service.set(
        "get_customer",
        {"customer_id": "CUST-1001"},
        {"status": "ok"},
        ttl_seconds=60,
    )


def test_action_tools_never_cached() -> None:
    fake_redis = FakeRedisClient()
    service = CacheService(redis_client=fake_redis)  # type: ignore[arg-type]

    service.set(
        "create_ticket",
        {"title": "x"},
        {"status": "waiting_approval"},
        ttl_seconds=60,
    )
    assert len(fake_redis.store) == 0


def test_executor_with_cache_integration() -> None:
    factory = make_seeded_sqlite_session_factory()
    fake_redis = FakeRedisClient()
    cache_service = CacheService(redis_client=fake_redis)  # type: ignore[arg-type]
    executor = ToolExecutor(factory, cache_service=cache_service)

    res1 = executor.execute_get_customer("CUST-1001")
    assert res1.status == ToolCallStatus.OK
    assert len(fake_redis.store) == 1

    res2 = executor.execute_get_customer("CUST-1001")
    assert res2.status == ToolCallStatus.OK
    assert res2.result["customer_id"] == "CUST-1001"
