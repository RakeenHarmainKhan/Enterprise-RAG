"""Query routers: LLM classifier, rules, always-hybrid."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from app.core.llm import LLMProvider
from app.core.registry import PluginRegistry


class RouteDecision(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


@runtime_checkable
class QueryRouter(Protocol):
    async def route(self, query: str, **kwargs: Any) -> RouteDecision: ...


router_registry: PluginRegistry[QueryRouter] = PluginRegistry()


class _RouterBase(ABC):
    @abstractmethod
    async def route(self, query: str, **kwargs: Any) -> RouteDecision:
        raise NotImplementedError


@router_registry.register("classifier")
class ClassifierRouter(_RouterBase):
    """LLM chooses retrieval mode from a constrained set."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def route(self, query: str, **kwargs: Any) -> RouteDecision:
        system = (
            "You are a retrieval router. Reply with exactly one token: "
            "dense, sparse, or hybrid. "
            "dense for paraphrase/semantic questions, sparse for keyword/ID lookups, "
            "hybrid when both matter."
        )
        user = f"Query: {query[:2000]}"
        text = await self._llm.acomplete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=8,
        )
        token = text.strip().split()[0].lower().rstrip(".,)")
        if token in {"dense", "sparse", "hybrid"}:
            return RouteDecision(token)
        return RouteDecision.HYBRID


@router_registry.register("rules")
class RuleBasedRouter(_RouterBase):
    """Heuristic routing from query shape."""

    async def route(self, query: str, **kwargs: Any) -> RouteDecision:
        q = query.strip()
        if len(q) < 4:
            return RouteDecision.SPARSE
        if any(c.isdigit() for c in q) and len(q) < 40:
            return RouteDecision.SPARSE
        if " OR " in q or " AND " in q:
            return RouteDecision.SPARSE
        return RouteDecision.HYBRID


@router_registry.register("hybrid")
class AlwaysHybridRouter(_RouterBase):
    async def route(self, query: str, **kwargs: Any) -> RouteDecision:
        return RouteDecision.HYBRID


def build_router(name: str, llm: LLMProvider | None = None, **kwargs: Any) -> QueryRouter:
    if name == "classifier":
        if llm is None:
            raise ValueError("ClassifierRouter requires llm")
        return ClassifierRouter(llm)
    if name == "rules":
        return RuleBasedRouter()
    if name == "hybrid":
        return AlwaysHybridRouter()
    return router_registry.build(name, **kwargs)
