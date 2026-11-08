"""LLM provider abstraction via LiteLLM with streaming support."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

import litellm
from pydantic import BaseModel

from app.core.config import LLMConfig, Settings


@runtime_checkable
class LLMProvider(Protocol):
    """Contract for text generation (sync chunks or async streaming)."""

    async def acomplete(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...

    async def astream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...


class LiteLLMProvider:
    """LiteLLM-backed provider; supports OpenAI-compatible APIs and more."""

    def __init__(self, llm: LLMConfig, settings: Settings) -> None:
        self._llm = llm
        self._settings = settings
        if settings.openai_api_key:
            litellm.api_key = settings.openai_api_key

    def _model(self) -> str:
        if self._llm.provider and self._llm.provider != "openai":
            return f"{self._llm.provider}/{self._llm.model}"
        return self._llm.model

    async def acomplete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        kwargs.setdefault("temperature", self._llm.temperature)
        kwargs.setdefault("max_tokens", self._llm.max_tokens)
        kwargs.setdefault("timeout", self._llm.timeout_seconds)
        resp = await litellm.acompletion(
            model=self._model(),
            messages=messages,
            stream=False,
            **kwargs,
        )
        choice = resp.choices[0]
        content = choice.message.content
        return content or ""

    async def astream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        kwargs.setdefault("temperature", self._llm.temperature)
        kwargs.setdefault("max_tokens", self._llm.max_tokens)
        kwargs.setdefault("timeout", self._llm.timeout_seconds)
        response = await litellm.acompletion(
            model=self._model(),
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:  # type: ignore[union-attr]
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content


class LLMFactory(BaseModel):
    """Factory wiring for ``LLMProvider``."""

    model_config = {"arbitrary_types_allowed": True}

    @staticmethod
    def create(llm_cfg: LLMConfig, settings: Settings) -> LLMProvider:
        return LiteLLMProvider(llm_cfg, settings)
