from __future__ import annotations

from typing import Any

from app.models.adapter import ModelAdapter, ModelMessage, ModelResponse


class FakeModelAdapter(ModelAdapter):
    def __init__(self, responses: list[ModelResponse] | None = None):
        self.responses = responses or []
        self.call_count = 0
        self.last_messages: list[ModelMessage] | None = None
        self.last_tools: list[dict[str, Any]] | None = None

    def get_provider_name(self) -> str:
        return "fake"

    def validate_config(self) -> None:
        pass

    async def chat(
        self, messages: list[ModelMessage], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        self.last_messages = messages
        self.last_tools = tools
        self.call_count += 1

        if self.responses:
            return self.responses.pop(0)

        # Default: no tool calls, empty response
        return ModelResponse(content="I don't have a response configured.")

    def set_responses(self, responses: list[ModelResponse]) -> None:
        self.responses = responses


class FakeModelAdapterWithToolCalls(FakeModelAdapter):
    def __init__(self, tool_name: str, arguments: dict[str, Any], call_id: str = "call_123"):
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments
        self.call_id = call_id

    async def chat(
        self, messages: list[ModelMessage], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        self.call_count += 1
        from app.models.adapter import ToolCall

        return ModelResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id=self.call_id,
                    type="function",
                    function={"name": self.tool_name, "arguments": self.arguments},
                )
            ],
            finish_reason="tool_calls",
        )
