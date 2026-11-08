"""Embedding plugins: OpenAI API and local sentence-transformers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import IngestionError
from app.core.registry import PluginRegistry


@runtime_checkable
class EmbedderPlugin(Protocol):
    def embed(self, text: str, **kwargs: Any) -> list[float]: ...

    def embed_many(self, texts: list[str], **kwargs: Any) -> list[list[float]]: ...

    @property
    def dimension(self) -> int: ...


class _BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, text: str, **kwargs: Any) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_many(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError


embedder_registry: PluginRegistry[EmbedderPlugin] = PluginRegistry()


@embedder_registry.register("openai")
class OpenAIEmbedder(_BaseEmbedder):
    """OpenAI-compatible embedding HTTP API."""

    def __init__(self, settings: Settings, model: str | None = None, batch_size: int = 32) -> None:
        self._settings = settings
        self._model = model or settings.embedding_model
        self._batch_size = batch_size
        self._dim: int | None = None

    @property
    def dimension(self) -> int:
        if self._dim is None:
            v = self.embed("dimension probe")
            self._dim = len(v)
        return self._dim

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8))
    def _post(self, inputs: list[str]) -> list[list[float]]:
        key = self._settings.openai_api_key
        if not key:
            raise IngestionError("OPENAI_API_KEY required for OpenAIEmbedder")
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {"model": self._model, "input": inputs}
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        return self.embed_many([text], **kwargs)[0]

    def embed_many(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not texts:
            return []
        bs = int(kwargs.get("batch_size", self._batch_size))
        out: list[list[float]] = []
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            out.extend(self._post(batch))
        return out


@embedder_registry.register("local")
class LocalEmbedder(_BaseEmbedder):
    """Sentence-transformers model (lazy-loaded)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _ensure(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        m = self._ensure()
        return int(m.get_sentence_embedding_dimension())

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        vec = self._ensure().encode(text, convert_to_numpy=True)
        return vec.astype(float).tolist()

    def embed_many(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not texts:
            return []
        batch_size = int(kwargs.get("batch_size", 32))
        vecs = self._ensure().encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [v.astype(float).tolist() for v in np.atleast_2d(vecs)]


def build_embedder(name: str, settings: Settings, **params: Any) -> EmbedderPlugin:
    if name == "openai":
        return OpenAIEmbedder(
            settings,
            model=params.get("model"),
            batch_size=int(params.get("batch_size", 32)),
        )
    if name == "local":
        return LocalEmbedder(model_name=str(params.get("model", "all-MiniLM-L6-v2")))
    return embedder_registry.build(name, **params)
