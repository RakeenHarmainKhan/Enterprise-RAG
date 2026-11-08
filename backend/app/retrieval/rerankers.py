"""Reranker plugins: cross-encoder and passthrough."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Protocol, runtime_checkable

from sentence_transformers import CrossEncoder

from app.core.registry import PluginRegistry
from app.retrieval.strategies import StrategyHit


@runtime_checkable
class RerankerPlugin(Protocol):
    def rerank(self, query: str, hits: list[StrategyHit], top_k: int, **kwargs: Any) -> list[StrategyHit]: ...


reranker_registry: PluginRegistry[RerankerPlugin] = PluginRegistry()


class _RerankerBase(ABC):
    @abstractmethod
    def rerank(self, query: str, hits: list[StrategyHit], top_k: int, **kwargs: Any) -> list[StrategyHit]:
        raise NotImplementedError


@reranker_registry.register("cross_encoder")
class CrossEncoderReranker(_RerankerBase):
    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self._model_name = model
        self._model: CrossEncoder | None = None

    def _ensure(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(self, query: str, hits: list[StrategyHit], top_k: int, **kwargs: Any) -> list[StrategyHit]:
        if not hits:
            return []
        model = self._ensure()
        pairs = [[query, h.text] for h in hits]
        scores = model.predict(pairs, show_progress_bar=False)
        scored = sorted(
            zip(hits, scores, strict=True),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        return [replace(h, score=float(s)) for h, s in scored[:top_k]]


@reranker_registry.register("passthrough")
class PassthroughReranker(_RerankerBase):
    def rerank(self, query: str, hits: list[StrategyHit], top_k: int, **kwargs: Any) -> list[StrategyHit]:
        return hits[:top_k]


def build_reranker(name: str, **params: Any) -> RerankerPlugin:
    if name == "cross_encoder":
        return CrossEncoderReranker(model=str(params.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2")))
    if name in {"passthrough", "none"}:
        return PassthroughReranker()
    return reranker_registry.build(name, **params)
