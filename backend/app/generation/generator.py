"""Generation engine: retrieval hook, context, stream, citations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.config import GenerationConfig, YamlAppConfig
from app.core.exceptions import GenerationError
from app.core.llm import LLMProvider
from app.generation.citations import CitationExtractor
from app.generation.context_builder import ContextBuilder
from app.retrieval.engine import RetrievalEngine, RetrievedChunk


class GenerationEngine:
    def __init__(
        self,
        yaml_cfg: YamlAppConfig,
        llm: LLMProvider,
        retrieval_engine: RetrievalEngine,
    ) -> None:
        self._cfg: GenerationConfig = yaml_cfg.generation
        self._llm = llm
        self._retrieval = retrieval_engine
        self._context = ContextBuilder(max_tokens=self._cfg.context_window_tokens)
        self._citations = CitationExtractor()

    async def generate(
        self,
        query: str,
        *,
        collection_id: str | None = None,
        chunks: list[RetrievedChunk] | None = None,
    ) -> dict[str, Any]:
        if chunks is None:
            chunks = await self._retrieval.retrieve(query, collection_id=collection_id)
        ctx, sources = self._context.build(query, chunks)
        messages = [
            {
                "role": "system",
                "content": "You are an enterprise assistant. Answer using only the provided context. "
                "Include citations like [1], [2] referring to excerpt numbers.",
            },
            {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {query}"},
        ]
        try:
            text = await self._llm.acomplete(messages)
        except Exception as e:
            raise GenerationError(str(e)) from e
        cites = self._citations.extract(text, sources)
        return {
            "answer": text,
            "sources": sources,
            "citations": cites,
            "chunks_used": len(sources),
            "retrieval_chunks": [
                {"text": c.text, "chunk_id": c.chunk_id, "document_id": c.document_id} for c in chunks
            ],
        }

    async def generate_stream(
        self,
        query: str,
        *,
        collection_id: str | None = None,
        chunks: list[RetrievedChunk] | None = None,
    ) -> AsyncIterator[str]:
        if chunks is None:
            chunks = await self._retrieval.retrieve(query, collection_id=collection_id)
        ctx, _sources = self._context.build(query, chunks)
        messages = [
            {
                "role": "system",
                "content": "You are an enterprise assistant. Answer using only the provided context. "
                "Include citations like [1], [2] referring to excerpt numbers.",
            },
            {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {query}"},
        ]
        try:
            async for token in self._llm.astream(messages):
                yield token
        except Exception as e:
            raise GenerationError(str(e)) from e
