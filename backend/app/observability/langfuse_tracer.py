"""Langfuse client wrapper and tracing decorator."""

from __future__ import annotations

import contextlib
import contextvars
import functools
import inspect
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from langfuse import Langfuse

from app.core.config import ObservabilityConfig, Settings, YamlAppConfig

P = ParamSpec("P")
R = TypeVar("R")


class LangfuseTracer:
    def __init__(self, yaml_cfg: YamlAppConfig, settings: Settings) -> None:
        self._cfg: ObservabilityConfig = yaml_cfg.observability
        self._settings = settings
        self._client: Langfuse | None = None
        if (
            self._cfg.langfuse_enabled
            and settings.langfuse_secret_key
            and settings.langfuse_public_key
        ):
            self._client = Langfuse(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_base_url,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Langfuse | None:
        return self._client

    def flush(self) -> None:
        if self._client:
            self._client.flush()


_tracer_var: contextvars.ContextVar[LangfuseTracer | None] = contextvars.ContextVar(
    "langfuse_tracer",
    default=None,
)


def set_current_tracer(tracer: LangfuseTracer | None) -> contextvars.Token[LangfuseTracer | None]:
    return _tracer_var.set(tracer)


def reset_current_tracer(token: contextvars.Token[LangfuseTracer | None]) -> None:
    _tracer_var.reset(token)


def get_current_tracer() -> LangfuseTracer | None:
    return _tracer_var.get()


def trace_span(name: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator: records a Langfuse trace when a tracer is bound via ``set_current_tracer``."""

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        span_name = name or fn.__name__

        @functools.wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            tracer = get_current_tracer()
            client = tracer.client if tracer and tracer.enabled else None
            if client is None:
                return await fn(*args, **kwargs)  # type: ignore[misc]
            trace_obj = None
            try:
                trace_obj = client.trace(name=span_name)
            except Exception:  # noqa: BLE001
                trace_obj = None
            try:
                return await fn(*args, **kwargs)  # type: ignore[misc]
            finally:
                if trace_obj is not None:
                    end = getattr(trace_obj, "end", None)
                    if callable(end):
                        with contextlib.suppress(Exception):
                            end()

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return fn(*args, **kwargs)

        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator
