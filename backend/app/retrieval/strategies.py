"""Retriever strategies: dense knn, sparse BM25, hybrid."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from opensearchpy import OpenSearch

from app.core.exceptions import RetrievalError
from app.core.registry import PluginRegistry
from app.retrieval.router import RouteDecision


@dataclass
class StrategyHit:
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    strategy: str = ""


@runtime_checkable
class RetrieverPlugin(Protocol):
    def search(
        self,
        query: str,
        embedding: list[float] | None,
        k: int,
        collection_id: str | None,
        **kwargs: Any,
    ) -> list[StrategyHit]: ...


retriever_registry: PluginRegistry[RetrieverPlugin] = PluginRegistry()


class _OpenSearchRetrieverBase:
    def __init__(self, client: OpenSearch, index_name: str) -> None:
        self._client = client
        self._index = index_name


@retriever_registry.register("dense")
class DenseRetriever(_OpenSearchRetrieverBase):
    def search(
        self,
        query: str,
        embedding: list[float] | None,
        k: int,
        collection_id: str | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        if not embedding:
            raise RetrievalError("DenseRetriever requires query embedding")
        knn_inner: dict[str, Any] = {
            "vector": embedding,
            "k": k,
        }
        if collection_id:
            knn_inner["filter"] = {"term": {"collection_id": collection_id}}
        body: dict[str, Any] = {
            "size": k,
            "query": {"knn": {"embedding": knn_inner}},
        }
        try:
            resp = self._client.search(index=self._index, body=body)
        except Exception as e:
            raise RetrievalError(f"Dense search failed: {e}") from e
        return self._hits(resp, "dense")

    def _hits(self, resp: Any, name: str) -> list[StrategyHit]:
        out: list[StrategyHit] = []
        for h in resp.get("hits", {}).get("hits", []):
            src = h.get("_source", {})
            out.append(
                StrategyHit(
                    chunk_id=src.get("chunk_id", h.get("_id", "")),
                    document_id=src.get("document_id", ""),
                    text=src.get("text", ""),
                    score=float(h.get("_score", 0.0)),
                    metadata=src.get("metadata") or {},
                    strategy=name,
                )
            )
        return out


@retriever_registry.register("sparse")
class SparseRetriever(_OpenSearchRetrieverBase):
    def search(
        self,
        query: str,
        embedding: list[float] | None,
        k: int,
        collection_id: str | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        must: list[dict[str, Any]] = [{"match": {"text": {"query": query}}}]
        if collection_id:
            must.append({"term": {"collection_id": collection_id}})
        body = {"size": k, "query": {"bool": {"must": must}}}
        try:
            resp = self._client.search(index=self._index, body=body)
        except Exception as e:
            raise RetrievalError(f"Sparse search failed: {e}") from e
        return self._to_hits(resp, "sparse")

    def _to_hits(self, resp: Any, name: str) -> list[StrategyHit]:
        out: list[StrategyHit] = []
        for h in resp.get("hits", {}).get("hits", []):
            src = h.get("_source", {})
            out.append(
                StrategyHit(
                    chunk_id=src.get("chunk_id", h.get("_id", "")),
                    document_id=src.get("document_id", ""),
                    text=src.get("text", ""),
                    score=float(h.get("_score", 0.0)),
                    metadata=src.get("metadata") or {},
                    strategy=name,
                )
            )
        return out


@retriever_registry.register("hybrid_strategy")
class HybridRetriever(_OpenSearchRetrieverBase):
    """OpenSearch ``hybrid`` query: knn + lexical in one request."""

    def search(
        self,
        query: str,
        embedding: list[float] | None,
        k: int,
        collection_id: str | None,
        **kwargs: Any,
    ) -> list[StrategyHit]:
        if not embedding:
            raise RetrievalError("HybridRetriever requires embedding")
        knn_clause: dict[str, Any] = {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": k,
                }
            }
        }
        if collection_id:
            knn_clause["knn"]["embedding"]["filter"] = {"term": {"collection_id": collection_id}}
        text_clause = {"match": {"text": {"query": query}}}
        if collection_id:
            text_clause = {
                "bool": {
                    "must": [text_clause],
                    "filter": [{"term": {"collection_id": collection_id}}],
                }
            }
        body = {
            "size": k,
            "query": {"hybrid": {"queries": [text_clause, knn_clause]}},
        }
        try:
            resp = self._client.search(index=self._index, body=body)
        except Exception as e:
            raise RetrievalError(f"Hybrid search failed: {e}") from e
        out: list[StrategyHit] = []
        for h in resp.get("hits", {}).get("hits", []):
            src = h.get("_source", {})
            out.append(
                StrategyHit(
                    chunk_id=src.get("chunk_id", h.get("_id", "")),
                    document_id=src.get("document_id", ""),
                    text=src.get("text", ""),
                    score=float(h.get("_score", 0.0)),
                    metadata=src.get("metadata") or {},
                    strategy="hybrid",
                )
            )
        return out


def build_retriever(name: str, client: OpenSearch, index_name: str) -> RetrieverPlugin:
    if name == "dense":
        return DenseRetriever(client, index_name)
    if name == "sparse":
        return SparseRetriever(client, index_name)
    if name in {"hybrid", "hybrid_strategy"}:
        return HybridRetriever(client, index_name)
    return retriever_registry.build(name, client, index_name)


def select_strategies(
    decision: RouteDecision,
    configured: list[tuple[str, float, dict[str, Any]]],
) -> list[tuple[str, float, dict[str, Any]]]:
    """Filter strategy list by router decision."""
    if decision == RouteDecision.HYBRID:
        return configured
    if decision == RouteDecision.DENSE:
        return [c for c in configured if c[0] in {"dense", "hybrid_strategy", "hybrid"}] or configured
    return [c for c in configured if c[0] in {"sparse", "hybrid_strategy", "hybrid"}] or configured
