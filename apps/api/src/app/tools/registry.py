from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.contracts import ErrorCategory, ToolCallStatus, ToolResult


class ToolDefinition(BaseModel):
    name: str = Field(pattern=r"^[a-z_]+$")
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel] | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[..., ToolResult]] = {}

    def register(self, definition: ToolDefinition, handler: Callable[..., ToolResult]) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def is_allowed(self, name: str) -> bool:
        return name in self._tools

    def get_definition(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def validate_call(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        definition = self._tools.get(name)
        if definition is None:
            return False, f"Unknown tool: {name}"
        try:
            definition.input_schema.model_validate(arguments)
        except ValidationError as e:
            return False, f"Invalid arguments for {name}: {e}"
        return True, None

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        valid, error = self.validate_call(name, arguments)
        if not valid:
            return ToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=error,
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        handler = self._handlers[name]
        try:
            result = handler(**arguments)
            if not isinstance(result, ToolResult):
                return ToolResult(
                    tool_name=name,
                    status=ToolCallStatus.ERROR,
                    error="Malformed tool output: expected ToolResult",
                    error_category=ErrorCategory.INVALID_RESPONSE,
                )
            return result
        except Exception as e:  # noqa: BLE001
            return ToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )

    def get_tools_for_model(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for definition in self._tools.values():
            schema = definition.input_schema.model_json_schema()
            # Remove title/description from schema for compactness
            params: dict[str, Any] = {
                "type": "object",
                "properties": schema.get("properties", {}),
            }
            if "required" in schema:
                params["required"] = schema["required"]
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": params,
                    },
                }
            )
        return tools


# ---------------------------------------------------------------------------
# Input schemas for the three TASK-003/tools — strictly validated
# ---------------------------------------------------------------------------


class GetCustomerArgs(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


class GetOrderArgs(BaseModel):
    order_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


class SearchDatabaseArgs(BaseModel):
    entity: str = Field(pattern=r"^(customers|orders|documents)$")
    filters: dict[str, Any] = Field(default_factory=dict)


# Sentinel for “no more tools needed” is handled by returning final_answer directly
# from the model adapter (content + no tool_calls).

REGISTRY = ToolRegistry()
