"""OpenSearch indexer plugin with knn + BM25 mapping."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from opensearchpy import OpenSearch, helpers

from app.core.exceptions import IngestionError
from app.core.registry import PluginRegistry


@runtime_checkable
class IndexerPlugin(Protocol):
    def ensure_index(self, dimension: int, **kwargs: Any) -> None: ...

    def bulk_index(self, documents: list[dict[str, Any]], **kwargs: Any) -> int: ...

    def delete_by_document(self, document_id: str, **kwargs: Any) -> int: ...


indexer_registry: PluginRegistry[IndexerPlugin] = PluginRegistry()


@indexer_registry.register("opensearch")
class OpenSearchIndexer:
    def __init__(
        self,
        client: OpenSearch,
        index_name: str = "enterprise_rag_chunks",
    ) -> None:
        self._client = client
        self._index = index_name

    def _mapping(self, dimension: int) -> dict[str, Any]:
        return {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "collection_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "title": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "lucene",
                        },
                    },
                    "metadata": {"type": "object", "enabled": True},
                }
            },
        }

    def ensure_index(self, dimension: int, **kwargs: Any) -> None:
        index = kwargs.get("index_name", self._index)
        if self._client.indices.exists(index=index):
            return
        self._client.indices.create(index=index, body=self._mapping(dimension))

    def bulk_index(self, documents: list[dict[str, Any]], **kwargs: Any) -> int:
        index = kwargs.get("index_name", self._index)
        actions = []
        for doc in documents:
            _id = doc.get("chunk_id") or str(uuid4())
            actions.append(
                {
                    "_index": index,
                    "_id": _id,
                    "_source": {**doc, "chunk_id": _id},
                }
            )
        if not actions:
            return 0
        success, errors = helpers.bulk(self._client, actions, refresh="wait_for")
        if errors:
            raise IngestionError(f"Bulk index errors: {errors}")
        return int(success)

    def delete_by_document(self, document_id: str, **kwargs: Any) -> int:
        index = kwargs.get("index_name", self._index)
        body = {"query": {"term": {"document_id": document_id}}}
        resp = self._client.delete_by_query(index=index, body=body, refresh=True)
        return int(resp.get("deleted", 0))


def build_indexer(name: str, client: OpenSearch, **params: Any) -> IndexerPlugin:
    if name == "opensearch":
        return OpenSearchIndexer(client, index_name=str(params.get("index_name", "enterprise_rag_chunks")))
    return indexer_registry.build(name, client, **params)
