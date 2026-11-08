"""Rank fusion: RRF and weighted sum."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Protocol, runtime_checkable

from app.core.registry import PluginRegistry
from app.retrieval.strategies import StrategyHit


@runtime_checkable
class FusionStrategy(Protocol):
    def fuse(self, ranked_lists: list[list[StrategyHit]], weights: list[float] | None, **kwargs: Any) -> list[StrategyHit]: ...


fusion_registry: PluginRegistry[FusionStrategy] = PluginRegistry()


class _FusionBase(ABC):
    @abstractmethod
    def fuse(
        self,
        ranked_lists: list[list[StrategyHit]],
        weights: list[float] | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        raise NotImplementedError


@fusion_registry.register("rrf")
class ReciprocalRankFusion(_FusionBase):
    def fuse(
        self,
        ranked_lists: list[list[StrategyHit]],
        weights: list[float] | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        k = int(kwargs.get("k", 60))
        scores: dict[str, float] = {}
        best_hit: dict[str, StrategyHit] = {}
        w = weights or [1.0] * len(ranked_lists)
        for wi, lst in zip(w, ranked_lists, strict=False):
            for rank, hit in enumerate(lst, start=1):
                cid = hit.chunk_id or hit.text[:80]
                scores[cid] = scores.get(cid, 0.0) + wi * (1.0 / (k + rank))
                best_hit.setdefault(cid, hit)
        ordered_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [replace(best_hit[key], score=scores[key]) for key in ordered_keys]


@fusion_registry.register("weighted_sum")
class WeightedSumFusion(_FusionBase):
    def fuse(
        self,
        ranked_lists: list[list[StrategyHit]],
        weights: list[float] | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        w = weights or [1.0] * len(ranked_lists)
        acc: dict[str, float] = {}
        best_hit: dict[str, StrategyHit] = {}
        for wi, lst in zip(w, ranked_lists, strict=False):
            if not lst:
                continue
            max_s = max(h.score for h in lst) or 1.0
            for hit in lst:
                cid = hit.chunk_id or hit.text[:80]
                norm = hit.score / max_s
                acc[cid] = acc.get(cid, 0.0) + wi * norm
                best_hit.setdefault(cid, hit)
        ordered_keys = sorted(acc.keys(), key=lambda x: acc[x], reverse=True)
        return [replace(best_hit[key], score=acc[key]) for key in ordered_keys]


def build_fusion(name: str, **kwargs: Any) -> FusionStrategy:
    if name in {"rrf", "reciprocal_rank"}:
        return ReciprocalRankFusion()
    if name in {"weighted_sum", "weighted"}:
        return WeightedSumFusion()
    return fusion_registry.build(name, **kwargs)
