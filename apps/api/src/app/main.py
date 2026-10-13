from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import approvals, health, runs
from app.config import get_settings
from app.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    description = "AI Operations Agent API foundation (TASK-001). Features are not yet implemented."
    app = FastAPI(title=settings.app_name, version="0.1.0", description=description)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(approvals.router)
    app.include_router(runs.router)
    return app


app = create_app()
