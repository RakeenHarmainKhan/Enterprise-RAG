"""Orchestrates parse → chunk → enrich → embed → index."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from opensearchpy import OpenSearch

from app.core.config import IngestionConfig, Settings, YamlAppConfig
from app.core.exceptions import IngestionError
from app.ingestion.chunkers import SemanticChunker, build_chunker
from app.ingestion.embedders import EmbedderPlugin, build_embedder
from app.ingestion.enrichers import MetadataEnricher
from app.ingestion.indexers import build_indexer
from app.ingestion.parsers import build_parser


class IngestionPipeline:
    def __init__(
        self,
        yaml_cfg: YamlAppConfig,
        settings: Settings,
        opensearch: OpenSearch,
        embedder: EmbedderPlugin | None = None,
    ) -> None:
        self._yaml = yaml_cfg
        self._settings = settings
        self._ing: IngestionConfig = yaml_cfg.ingestion
        self._os = opensearch
        self._enricher = MetadataEnricher()
        embed_params = dict(self._ing.embedder_params)
        self._embedder = embedder or build_embedder(self._ing.embedder, settings, **embed_params)
        indexer_params = dict(self._ing.indexer_params)
        self._indexer = build_indexer(self._ing.indexer, opensearch, **indexer_params)

    def ingest_file(
        self,
        file_path: Path,
        *,
        document_id: str | None = None,
        collection_id: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        doc_id = document_id or str(uuid4())
        fname = filename or file_path.name
        suffix = file_path.suffix.lower()
        parser_name = self._ing.parser
        if suffix == ".pdf":
            parser_name = "pdf"
        elif suffix in {".docx"}:
            parser_name = "docx"
        elif suffix in {".html", ".htm"}:
            parser_name = "html"
        elif suffix in {".md", ".markdown"}:
            parser_name = "markdown"

        parser = build_parser(parser_name, **self._ing.parser_params)
        text = parser.parse(file_path)
        if not text.strip():
            raise IngestionError("No text extracted from document")

        chunker = build_chunker(self._ing.chunker, **self._ing.chunker_params)
        if self._ing.chunker == "semantic" and isinstance(chunker, SemanticChunker):
            chunks = chunker.chunk(
                text,
                embed_fn=lambda sents: self._embedder.embed_many(sents),
                **self._ing.chunker_params,
            )
        else:
            chunks = chunker.chunk(text, **self._ing.chunker_params)

        self._indexer.ensure_index(self._embedder.dimension, **self._ing.indexer_params)

        vectors = self._embedder.embed_many(chunks, **self._ing.embedder_params)
        if len(vectors) != len(chunks):
            raise IngestionError("Embedding batch size mismatch")

        bulk_docs: list[dict[str, Any]] = []
        for i, (chunk, emb) in enumerate(zip(chunks, vectors, strict=True)):
            meta = self._enricher.enrich(
                chunk,
                filename=fname,
                extra={"chunk_index": i, "source_file": fname},
            )
            bulk_docs.append(
                {
                    "chunk_id": f"{doc_id}:{i}",
                    "document_id": doc_id,
                    "collection_id": collection_id or "default",
                    "text": chunk,
                    "title": meta.get("title"),
                    "embedding": emb,
                    "metadata": meta,
                }
            )

        indexed = self._indexer.bulk_index(bulk_docs, **self._ing.indexer_params)
        return {
            "document_id": doc_id,
            "chunks": len(chunks),
            "indexed": indexed,
            "filename": fname,
            "collection_id": collection_id or "default",
        }
