from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import create_sync_engine, get_session_factory
from app.evals.evaluation_service import EvaluationService
from app.models.adapter import ModelConfig
from app.models.openai_adapter import create_model_adapter
from app.tools.executor import ToolExecutor
from app.tools.registry import (
    CalculateArgs,
    GetCustomerArgs,
    GetOrderArgs,
    SearchDatabaseArgs,
    SearchDocumentsArgs,
    ToolDefinition,
    ToolRegistry,
)

router = APIRouter(prefix="/api/v1/evals", tags=["evals"])


def verify_operator_role(
    x_operator_role: Annotated[str | None, Header()] = None,
) -> str:
    if not x_operator_role or x_operator_role.lower() != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator role required via X-Operator-Role header",
        )
    return x_operator_role


def get_db_session() -> Iterator[Session]:
    engine = create_sync_engine()
    factory = get_session_factory(engine)
    with factory() as session:
        yield session


@router.post("/run")
async def trigger_evaluation(
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    try:
        engine = create_sync_engine()
        factory = get_session_factory(engine)
        executor = ToolExecutor(factory)
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
            executor.execute_get_customer,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="get_order", description="x", input_schema=GetOrderArgs),
            executor.execute_get_order,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(
                name="search_database",
                description="x",
                input_schema=SearchDatabaseArgs,
            ),
            executor.execute_search_database,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(
                name="search_documents",
                description="x",
                input_schema=SearchDocumentsArgs,
            ),
            executor.execute_search_documents,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="calculate", description="x", input_schema=CalculateArgs),
            executor.execute_calculate,  # type: ignore[arg-type]
        )

        config = ModelConfig.from_env()
        adapter = create_model_adapter(config)

        service = EvaluationService(adapter, executor, registry, dataset_version="v1")
        report = await service.run_evaluation()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}") from e


@router.get("/reports")
def list_evaluation_reports(
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> list[str]:
    reports_dir = os.environ.get("EVAL_REPORTS_DIR") or os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "evals",
            "reports",
        )
    )
    try:
        files = sorted([f for f in os.listdir(reports_dir) if f.endswith(".json")])
    except OSError:
        return []
    return files
