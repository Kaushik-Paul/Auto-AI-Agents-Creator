import os
from typing import Any, AsyncGenerator, Mapping, Sequence

from autogen_core.models import ChatCompletionClient, CreateResult, RequestUsage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from pydantic import BaseModel

from main.constants import (
    OPENCODE_GO_ANTHROPIC_BASE_URL,
    OPENCODE_GO_OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
)

try:
    from autogen_ext.models.anthropic import AnthropicChatCompletionClient
except ImportError:  # pragma: no cover - caught early when OpenCode Anthropic models are used.
    AnthropicChatCompletionClient = None

load_dotenv(override=True)

DEFAULT_OPENROUTER_MODEL = "x-ai/grok-4-fast:free"
DEFAULT_OPENCODE_GO_MODEL = "minimax-m2.7"

MODEL_INFO = {
    "family": "unknown",
    "vision": False,
    "json_output": False,
    "function_calling": False,
    "structured_output": False,
}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class OpenCodeGoAutoClient(ChatCompletionClient):
    _protocol_cache: dict[str, str] = {}

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        openai_base_url: str,
        anthropic_base_url: str,
        temperature: float,
        api_style: str = "auto",
    ) -> None:
        self._model = model
        self._api_style = api_style.strip().lower()
        if self._api_style not in {"auto", "openai", "anthropic"}:
            raise ValueError("OPENCODE_GO_API_STYLE must be auto, openai, or anthropic")

        self._openai_client = OpenAIChatCompletionClient(
            model=model,
            base_url=openai_base_url,
            api_key=api_key,
            model_info=MODEL_INFO,
            temperature=temperature,
        )
        self._anthropic_client = None
        if AnthropicChatCompletionClient is not None:
            self._anthropic_client = AnthropicChatCompletionClient(
                model=model,
                base_url=anthropic_base_url,
                api_key=api_key,
                model_info=MODEL_INFO,
                temperature=temperature,
            )

        self._active_protocol = self._initial_protocol()

    @property
    def capabilities(self) -> dict[str, Any]:
        return MODEL_INFO

    @property
    def model_info(self) -> dict[str, Any]:
        return MODEL_INFO

    def _initial_protocol(self) -> str:
        if self._api_style != "auto":
            return self._api_style
        if self._model in self._protocol_cache:
            return self._protocol_cache[self._model]
        if self._model.startswith("minimax-"):
            return "anthropic"
        return "openai"

    def _client_for(self, protocol: str) -> ChatCompletionClient:
        if protocol == "openai":
            return self._openai_client
        if self._anthropic_client is None:
            raise RuntimeError(
                "OpenCode Go Anthropic-style models require autogen-ext[anthropic]."
            )
        return self._anthropic_client

    def _alternate_protocol(self) -> str:
        return "anthropic" if self._active_protocol == "openai" else "openai"

    async def create(
        self,
        messages: Sequence[Any],
        *,
        tools: Sequence[Any] = [],
        tool_choice: Any = "auto",
        json_output: bool | type[BaseModel] | None = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Any = None,
    ) -> CreateResult:
        create_args = {
            "tools": tools,
            "tool_choice": tool_choice,
            "json_output": json_output,
            "extra_create_args": extra_create_args,
            "cancellation_token": cancellation_token,
        }
        try:
            result = await self._client_for(self._active_protocol).create(
                messages, **create_args
            )
            self._protocol_cache[self._model] = self._active_protocol
            return result
        except Exception as first_error:
            if self._api_style != "auto":
                raise
            first_protocol = self._active_protocol
            self._active_protocol = self._alternate_protocol()
            try:
                result = await self._client_for(self._active_protocol).create(
                    messages, **create_args
                )
                self._protocol_cache[self._model] = self._active_protocol
                return result
            except Exception as second_error:
                raise RuntimeError(
                    f"OpenCode Go model '{self._model}' failed with both "
                    f"{first_protocol} and {self._active_protocol} API styles. "
                    f"First error: {first_error}"
                ) from second_error

    def create_stream(
        self,
        messages: Sequence[Any],
        *,
        tools: Sequence[Any] = [],
        tool_choice: Any = "auto",
        json_output: bool | type[BaseModel] | None = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Any = None,
    ) -> AsyncGenerator[str | CreateResult, None]:
        async def stream() -> AsyncGenerator[str | CreateResult, None]:
            stream_args = {
                "tools": tools,
                "tool_choice": tool_choice,
                "json_output": json_output,
                "extra_create_args": extra_create_args,
                "cancellation_token": cancellation_token,
            }
            try:
                async for chunk in self._client_for(
                    self._active_protocol
                ).create_stream(messages, **stream_args):
                    yield chunk
                self._protocol_cache[self._model] = self._active_protocol
            except Exception:
                if self._api_style != "auto":
                    raise
                self._active_protocol = self._alternate_protocol()
                async for chunk in self._client_for(
                    self._active_protocol
                ).create_stream(messages, **stream_args):
                    yield chunk
                self._protocol_cache[self._model] = self._active_protocol

        return stream()

    async def close(self) -> None:
        await self._openai_client.close()
        if self._anthropic_client is not None:
            await self._anthropic_client.close()

    def actual_usage(self) -> RequestUsage:
        return self._client_for(self._active_protocol).actual_usage()

    def total_usage(self) -> RequestUsage:
        openai_usage = self._openai_client.total_usage()
        if self._anthropic_client is None:
            return openai_usage
        anthropic_usage = self._anthropic_client.total_usage()
        return RequestUsage(
            prompt_tokens=openai_usage.prompt_tokens + anthropic_usage.prompt_tokens,
            completion_tokens=(
                openai_usage.completion_tokens + anthropic_usage.completion_tokens
            ),
        )

    def count_tokens(
        self, messages: Sequence[Any], *, tools: Sequence[Any] = []
    ) -> int:
        return self._client_for(self._active_protocol).count_tokens(
            messages, tools=tools
        )

    def remaining_tokens(
        self, messages: Sequence[Any], *, tools: Sequence[Any] = []
    ) -> int:
        return self._client_for(self._active_protocol).remaining_tokens(
            messages, tools=tools
        )


def create_model_client(*, temperature: float) -> ChatCompletionClient:
    if _env_bool("USE_OPENROUTER", default=False):
        return OpenAIChatCompletionClient(
            model=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            base_url=OPENROUTER_BASE_URL,
            api_key=_env_required("OPENROUTER_API_KEY"),
            model_info=MODEL_INFO,
            temperature=temperature,
        )

    return OpenCodeGoAutoClient(
        model=os.getenv("OPENCODE_GO_MODEL", DEFAULT_OPENCODE_GO_MODEL),
        openai_base_url=OPENCODE_GO_OPENAI_BASE_URL,
        anthropic_base_url=OPENCODE_GO_ANTHROPIC_BASE_URL,
        api_key=_env_required("OPENCODE_GO_API_KEY"),
        temperature=temperature,
        api_style=os.getenv("OPENCODE_GO_API_STYLE", "auto"),
    )
