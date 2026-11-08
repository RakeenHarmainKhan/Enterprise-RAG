"""Metadata enrichment for chunks (title, dates, simple entities)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class MetadataEnricher:
    """Derive lightweight metadata from chunk text and file context."""

    _date_patterns = [
        re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b"),
        re.compile(r"\b(\d{1,2}/\d{1,2}/20\d{2})\b"),
    ]

    def enrich(
        self,
        chunk_text: str,
        *,
        filename: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "title": self._infer_title(chunk_text, filename),
            "extracted_dates": self._extract_dates(chunk_text),
            "entities": self._simple_entities(chunk_text),
            "enriched_at": datetime.utcnow().isoformat() + "Z",
        }
        if extra:
            meta.update(extra)
        return meta

    def _infer_title(self, text: str, filename: str | None) -> str:
        for line in text.splitlines():
            line = line.strip()
            if 10 <= len(line) <= 120:
                return line
        return filename or "untitled"

    def _extract_dates(self, text: str) -> list[str]:
        found: set[str] = set()
        for pat in self._date_patterns:
            found.update(pat.findall(text))
        return sorted(found)

    def _simple_entities(self, text: str) -> list[dict[str, str]]:
        """Capitalized phrase heuristic (not NER)."""
        caps = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
        return [{"text": c, "type": "phrase"} for c in sorted(set(caps))[:20]]
