"""Redis-backed cache keyed by approximate nearest embedding match."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import redis.asyncio as redis

from app.core.config import CacheConfig, YamlAppConfig
from app.ingestion.embedders import EmbedderPlugin


class SemanticCache:
    def __init__(self, yaml_cfg: YamlAppConfig, redis_client: redis.Redis, embedder: EmbedderPlugin) -> None:
        self._cfg: CacheConfig = yaml_cfg.cache
        self._r = redis_client
        self._embedder = embedder
        self._prefix = "semcache:"

    def _key_main(self, query_hash: str) -> str:
        return f"{self._prefix}{query_hash}"

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        va = np.array(a, dtype=np.float64)
        vb = np.array(b, dtype=np.float64)
        n = np.linalg.norm(va) * np.linalg.norm(vb)
        if n == 0:
            return 0.0
        return float(np.dot(va, vb) / n)

    async def lookup(self, query: str) -> dict[str, Any] | None:
        qvec = self._embedder.embed(query)
        async for k in self._r.scan_iter(match=f"{self._prefix}*", count=100):
            key_s = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            raw = await self._r.get(key_s)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            ev = payload.get("embedding")
            if not ev:
                continue
            sim = self._cosine(qvec, ev)
            if sim >= self._cfg.similarity_threshold:
                return payload.get("value")
        return None

    async def store(self, query: str, value: dict[str, Any]) -> None:
        qvec = self._embedder.embed(query)
        h = str(abs(hash(query)) % (10**12))
        key = self._key_main(h)
        payload = json.dumps({"embedding": qvec, "value": value, "query": query[:500]})
        await self._r.setex(key, self._cfg.ttl_seconds, payload)

    async def clear_prefix(self) -> int:
        n = 0
        async for k in self._r.scan_iter(match=f"{self._prefix}*", count=200):
            key_s = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            await self._r.delete(key_s)
            n += 1
        return n
