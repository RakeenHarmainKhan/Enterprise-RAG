"""Simple async publish/subscribe event bus for internal telemetry hooks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)

Subscriber = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subs: list[Subscriber] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, handler: Subscriber) -> None:
        async with self._lock:
            self._subs.append(handler)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            handlers = list(self._subs)
        for h in handlers:
            try:
                await h(event)
            except Exception as e:  # noqa: BLE001
                log.warning("event_handler_failed", error=str(e), event_type=event.get("type"))
