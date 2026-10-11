from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis import Redis
from sqlalchemy.engine import Engine

from app.cache.redis_client import create_redis_client
from app.cache.redis_client import ping_ready as redis_ping_ready
from app.config import get_settings
from app.db.session import create_sync_engine
from app.db.session import ping_ready as db_ping_ready

router = APIRouter(tags=["health"])


class DependencyStatus(BaseModel):
    name: str
    status: str
    required: bool


class LivenessResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


def get_db_engine() -> Engine:
    return create_sync_engine()


def get_redis() -> Redis:
    return create_redis_client()


@router.get("/health/live", response_model=LivenessResponse)
def live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get("/health/ready")
def ready(
    engine: Annotated[Engine, Depends(get_db_engine)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> JSONResponse:
    settings = get_settings()
    configuration_ok = bool(settings.app_name)

    dependencies = [
        DependencyStatus(
            name="configuration",
            status="ok" if configuration_ok else "error",
            required=True,
        ),
        DependencyStatus(
            name="postgres",
            status="ok" if db_ping_ready(engine) else "error",
            required=True,
        ),
    ]

    if settings.redis_enabled:
        dependencies.append(
            DependencyStatus(
                name="redis",
                status="ok" if redis_ping_ready(redis_client) else "error",
                required=False,
            )
        )

    required_ok = all(dep.status == "ok" for dep in dependencies if dep.required)
    payload = ReadinessResponse(
        status="ok" if required_ok else "degraded",
        dependencies=dependencies,
    )
    return JSONResponse(status_code=200 if required_ok else 503, content=payload.model_dump())
