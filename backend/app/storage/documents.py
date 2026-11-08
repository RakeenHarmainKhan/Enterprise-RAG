"""Document metadata registry (filesystem + JSON index)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class DocumentStore:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir
        self._registry_path = base_dir / "documents_registry.json"
        self._lock = asyncio.Lock()
        self._docs: dict[str, dict[str, Any]] = {}

    async def load(self) -> None:
        self._base.mkdir(parents=True, exist_ok=True)
        if self._registry_path.is_file():
            raw = self._registry_path.read_text(encoding="utf-8")
            self._docs = json.loads(raw) if raw.strip() else {}
        else:
            self._docs = {}

    async def _persist(self) -> None:
        self._registry_path.write_text(json.dumps(self._docs, indent=2), encoding="utf-8")

    async def create_placeholder(
        self,
        *,
        filename: str,
        collection_id: str | None,
        content_type: str | None,
    ) -> str:
        doc_id = str(uuid4())
        async with self._lock:
            self._docs[doc_id] = {
                "id": doc_id,
                "filename": filename,
                "collection_id": collection_id or "default",
                "content_type": content_type,
                "status": "processing",
                "chunks": 0,
            }
            await self._persist()
        return doc_id

    async def mark_ready(self, doc_id: str, *, chunks: int, path: str) -> None:
        async with self._lock:
            if doc_id in self._docs:
                self._docs[doc_id]["status"] = "ready"
                self._docs[doc_id]["chunks"] = chunks
                self._docs[doc_id]["path"] = path
            await self._persist()

    async def mark_failed(self, doc_id: str, message: str) -> None:
        async with self._lock:
            if doc_id in self._docs:
                self._docs[doc_id]["status"] = "failed"
                self._docs[doc_id]["error"] = message
            await self._persist()

    async def list_docs(self) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._docs.values())

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        async with self._lock:
            d = self._docs.get(doc_id)
            return dict(d) if d else None

    async def delete(self, doc_id: str) -> bool:
        async with self._lock:
            existed = doc_id in self._docs
            self._docs.pop(doc_id, None)
            await self._persist()
        return existed

    def resolve_upload_dir(self, doc_id: str) -> Path:
        return self._base / doc_id
