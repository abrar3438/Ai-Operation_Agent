from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1 import health
from app.main import app


class _FakeRedis:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def ping(self) -> bool:
        return self._ok


def _client(db_ok: bool, redis_ok: bool) -> TestClient:
    app.dependency_overrides[health.get_db_engine] = lambda: object()
    app.dependency_overrides[health.get_redis] = lambda: _FakeRedis(redis_ok)
    health.db_ping_ready = lambda engine: db_ok  # type: ignore[assignment]
    health.redis_ping_ready = lambda client: redis_ok  # type: ignore[assignment]
    return TestClient(app)


def test_liveness_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_ok_when_dependencies_healthy() -> None:
    with _client(db_ok=True, redis_ok=True) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    names = {dep["name"] for dep in body["dependencies"]}
    assert {"configuration", "postgres", "redis"} <= names
    app.dependency_overrides.clear()


def test_readiness_degrades_when_db_down() -> None:
    with _client(db_ok=False, redis_ok=True) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    postgres = next(dep for dep in body["dependencies"] if dep["name"] == "postgres")
    assert postgres["status"] == "error"
    assert postgres["required"] is True
    app.dependency_overrides.clear()


def test_readiness_redis_optional() -> None:
    with _client(db_ok=True, redis_ok=False) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    redis = next(dep for dep in response.json()["dependencies"] if dep["name"] == "redis")
    assert redis["required"] is False
    app.dependency_overrides.clear()


def test_readiness_does_not_leak_secrets() -> None:
    with _client(db_ok=True, redis_ok=True) as client:
        response = client.get("/health/ready")
    assert "postgres:postgres" not in response.text
    assert "password" not in response.text.lower()
    app.dependency_overrides.clear()
