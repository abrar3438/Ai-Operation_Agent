from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.tools.registry import CalculateArgs, SearchDocumentsArgs


def test_search_documents_args_requires_nonempty_query() -> None:
    with pytest.raises(ValidationError):
        SearchDocumentsArgs(query="")


def test_search_documents_args_rejects_oversized_query() -> None:
    with pytest.raises(ValidationError):
        SearchDocumentsArgs(query="x" * 501)


def test_calculate_args_requires_operation() -> None:
    with pytest.raises(ValidationError):
        CalculateArgs.model_validate({"operation": "eval", "operands": [1, 2]})


def test_calculate_args_requires_two_operands() -> None:
    with pytest.raises(ValidationError):
        CalculateArgs(operation="add", operands=[1])


def test_calculate_supports_percent_and_total_cents() -> None:
    p = CalculateArgs(operation="percent", operands=[1000, 10])
    assert p.operation == "percent"
    t = CalculateArgs(operation="total_cents", operands=[12.50, 8.25])
    assert t.operands == [12.50, 8.25]


def test_executor_calculate_is_registerable() -> None:
    from app.tools.registry import ToolDefinition, ToolRegistry

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search_documents", description="doc search", input_schema=SearchDocumentsArgs
        ),
        lambda **kw: None,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="calculate", description="calc", input_schema=CalculateArgs),
        lambda **kw: None,  # type: ignore[arg-type]
    )
    names = registry.list_tools()
    assert "search_documents" in names and "calculate" in names
