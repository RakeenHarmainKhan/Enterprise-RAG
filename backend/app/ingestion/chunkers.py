"""Chunker plugins: fixed, recursive (llama-index), semantic."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

import numpy as np
from llama_index.core import Document as LIDocument
from llama_index.core.node_parser import SentenceSplitter

from app.core.exceptions import IngestionError
from app.core.registry import PluginRegistry


@runtime_checkable
class ChunkerPlugin(Protocol):
    def chunk(self, text: str, **kwargs: Any) -> list[str]: ...


class _BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str, **kwargs: Any) -> list[str]:
        raise NotImplementedError


chunker_registry: PluginRegistry[ChunkerPlugin] = PluginRegistry()


@chunker_registry.register("fixed")
class FixedSizeChunker(_BaseChunker):
    """Character-window chunking with overlap."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, **kwargs: Any) -> list[str]:
        size = int(kwargs.get("chunk_size", self.chunk_size))
        overlap = int(kwargs.get("chunk_overlap", self.chunk_overlap))
        if size <= 0:
            raise IngestionError("chunk_size must be positive")
        step = max(1, size - overlap)
        chunks: list[str] = []
        for i in range(0, len(text), step):
            piece = text[i : i + size].strip()
            if piece:
                chunks.append(piece)
        return chunks


@chunker_registry.register("recursive")
class RecursiveChunker(_BaseChunker):
    """Sentence-aware splitting via llama-index SentenceSplitter."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def chunk(self, text: str, **kwargs: Any) -> list[str]:
        chunk_size = int(kwargs.get("chunk_size", self._splitter.chunk_size))
        overlap = int(kwargs.get("chunk_overlap", self._splitter.chunk_overlap))
        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
        nodes = splitter.get_nodes_from_documents([LIDocument(text=text)])
        return [n.get_content(metadata_mode="none") for n in nodes if n.get_content(metadata_mode="none").strip()]


@chunker_registry.register("semantic")
class SemanticChunker(_BaseChunker):
    """Split on sentence boundaries when embedding cosine similarity drops."""

    def __init__(
        self,
        embed_fn: Any | None = None,
        similarity_threshold: float = 0.72,
        min_sentences_per_chunk: int = 2,
    ) -> None:
        self._embed_fn = embed_fn
        self.similarity_threshold = similarity_threshold
        self.min_sentences = min_sentences_per_chunk

    def _default_embed(self, sentences: list[str]) -> np.ndarray:
        if self._embed_fn is None:
            raise IngestionError("SemanticChunker requires embed_fn or inject LocalEmbedder.embed_many")
        return np.array(self._embed_fn(sentences), dtype=np.float32)

    def chunk(self, text: str, **kwargs: Any) -> list[str]:
        threshold = float(kwargs.get("similarity_threshold", self.similarity_threshold))
        min_s = int(kwargs.get("min_sentences_per_chunk", self.min_sentences))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sentences) <= min_s:
            return ["\n".join(sentences)] if sentences else []

        embed_fn = kwargs.get("embed_fn", self._default_embed)
        vecs = embed_fn(sentences)
        if vecs.shape[0] != len(sentences):
            raise IngestionError("Embedding count must match sentence count")

        def cos(a: np.ndarray, b: np.ndarray) -> float:
            na = np.linalg.norm(a) * np.linalg.norm(b)
            if na == 0:
                return 0.0
            return float(np.dot(a, b) / na)

        groups: list[list[str]] = []
        current: list[str] = [sentences[0]]
        for i in range(1, len(sentences)):
            sim = cos(vecs[i - 1], vecs[i])
            if sim < threshold and len(current) >= min_s:
                groups.append(current)
                current = [sentences[i]]
            else:
                current.append(sentences[i])
        if current:
            groups.append(current)
        return ["\n".join(g) for g in groups]


def build_chunker(name: str, **kwargs: Any) -> ChunkerPlugin:
    target = chunker_registry.resolve(name)
    if isinstance(target, type):
        return target(**kwargs)  # type: ignore[misc]
    return target(**kwargs)  # type: ignore[operator]
