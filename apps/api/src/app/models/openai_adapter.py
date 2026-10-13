from __future__ import annotations

import os
from typing import Any

import httpx

from app.models.adapter import (
    ModelAdapter,
    ModelAdapterError,
    ModelConfig,
    ModelMessage,
    ModelResponse,
    ToolCall,
)


class OpenAICompatibleAdapter(ModelAdapter):
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig.from_env()
        self._client: httpx.AsyncClient | None = None

    def get_provider_name(self) -> str:
        return "openai_compatible"

    def validate_config(self) -> None:
        if not self.config.api_key:
            raise ModelAdapterError(
                "LLM_API_KEY is required but not configured",
                category="config_error",
                retryable=False,
            )
        if not self.config.model:
            raise ModelAdapterError(
                "LLM_MODEL is required but not configured",
                category="config_error",
                retryable=False,
            )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            default_base = "https://api.craftx.corecraftsolutions.com/api/v1"
            endpoint_raw = os.getenv("CRAFTX_ENDPOINT")
            if endpoint_raw:
                default_base = endpoint_raw.rsplit("/chat/completions", 1)[0].rstrip("/")
            base_url = self.config.base_url or default_base
            api_key = self.config.api_key
            if api_key is None:  # validated above; mypy guard
                raise ModelAdapterError("Missing API key", category="config_error")
            headers = {
                "Authorization": f"Bearer {api_key.get_secret_value()}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout_seconds, connect=10.0),
            )
        return self._client

    def _map_messages(self, messages: list[ModelMessage]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            mapped: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                mapped["content"] = msg.content
            if msg.tool_calls:
                mapped["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                mapped["tool_call_id"] = msg.tool_call_id
            result.append(mapped)
        return result

    def _map_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        mapped = []
        for tool in tools:
            if tool.get("type") == "function":
                mapped.append({"type": "function", "function": tool.get("function", {})})
            else:
                mapped.append(tool)
        return mapped

    async def chat(  # noqa: E501
        self, messages: list[ModelMessage], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        self.validate_config()
        client = await self._get_client()

        payload = {
            "model": self.config.model,
            "messages": self._map_messages(messages),
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = self._map_tools(tools)
            payload["tool_choice"] = "auto"

        last_exception: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data)
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                # Retry only transient: 429 (rate limit), 5xx (server error)
                is_transient = status_code == 429 or status_code >= 500
                category = (
                    "rate_limit_error"
                    if status_code == 429
                    else (
                        "provider_error"
                        if status_code >= 500
                        else (
                            "authorization_error"
                            if status_code in (401, 403)
                            else "validation_error"
                        )
                    )
                )

                if is_transient and attempt < self.config.max_retries:
                    await self._backoff(attempt)
                    continue

                raise ModelAdapterError(
                    f"Provider HTTP error: {status_code}",
                    category=category,
                    retryable=is_transient,
                ) from e
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise ModelAdapterError(
                    "Provider request timeout",
                    category="timeout",
                    retryable=True,
                ) from e
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise ModelAdapterError(
                    f"Provider connection error: {str(e)}",
                    category="connection_error",
                    retryable=True,
                ) from e

        raise ModelAdapterError(
            f"Max retries exceeded: {str(last_exception)}",
            category="max_retries_exceeded",
            retryable=False,
        )

    async def _backoff(self, attempt: int) -> None:
        import asyncio

        delay = min(2**attempt, 30)
        await asyncio.sleep(delay)

    def _parse_response(self, data: dict[str, Any]) -> ModelResponse:
        choices = data.get("choices", [])
        if not choices:
            raise ModelAdapterError(
                "Empty choices in provider response", category="invalid_response"
            )

        choice = choices[0]
        message = choice.get("message", {})

        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc.get("id", ""),
                    type=tc.get("type", "function"),
                    function=tc.get("function", {}),
                )
                for tc in message["tool_calls"]
            ]

        return ModelResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            usage=data.get("usage"),
            finish_reason=choice.get("finish_reason"),
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


def create_model_adapter(config: ModelConfig | None = None) -> ModelAdapter:
    raw = config.provider if config else os.getenv("LLM_PROVIDER", "openai_compatible")
    provider = raw.lower()
    if provider == "openai_compatible":
        return OpenAICompatibleAdapter(config)
    raise ModelAdapterError(
        f"Unsupported provider: {provider}. Only 'openai_compatible' is supported.",
        category="config_error",
        retryable=False,
    )
