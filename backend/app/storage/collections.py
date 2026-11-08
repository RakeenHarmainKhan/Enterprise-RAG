"""Collection CRUD backed by JSON."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class CollectionStore:
    def __init__(self, base_dir: Path) -> None:
        self._path = base_dir / "collections.json"
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, Any]] = {}

    async def load(self) -> None:
        base_dir = self._path.parent
        base_dir.mkdir(parents=True, exist_ok=True)
        if self._path.is_file():
            raw = self._path.read_text(encoding="utf-8")
            self._data = json.loads(raw) if raw.strip() else {}
        else:
            self._data = {
                "default": {"id": "default", "name": "Default", "description": "Default collection"},
            }
            await self._persist()

    async def _persist(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def list_all(self) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._data.values())

    async def get(self, cid: str) -> dict[str, Any] | None:
        async with self._lock:
            d = self._data.get(cid)
            return dict(d) if d else None

    async def create(self, name: str, description: str = "") -> dict[str, Any]:
        cid = str(uuid4())
        rec = {"id": cid, "name": name, "description": description}
        async with self._lock:
            self._data[cid] = rec
            await self._persist()
        return rec

    async def update(self, cid: str, **fields: Any) -> dict[str, Any] | None:
        async with self._lock:
            if cid not in self._data:
                return None
            self._data[cid].update({k: v for k, v in fields.items() if v is not None})
            await self._persist()
            return dict(self._data[cid])

    async def delete(self, cid: str) -> bool:
        if cid == "default":
            return False
        async with self._lock:
            existed = cid in self._data
            self._data.pop(cid, None)
            await self._persist()
        return existed
