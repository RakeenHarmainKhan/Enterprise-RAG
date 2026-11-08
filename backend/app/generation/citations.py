"""Extract citation markers from model output and link to source chunks."""

from __future__ import annotations

import re
from typing import Any


class CitationExtractor:
    """Finds bracket-style citations like ``[1]`` or ``[1, 2]``."""

    _pattern = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

    def extract(self, answer: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_index = {int(s["index"]): s for s in sources if "index" in s}
        cited: dict[int, dict[str, Any]] = {}
        for m in self._pattern.finditer(answer):
            raw = m.group(1)
            for part in raw.split(","):
                part = part.strip()
                if not part.isdigit():
                    continue
                idx = int(part)
                if idx in by_index:
                    cited[idx] = by_index[idx]
        return [cited[k] for k in sorted(cited.keys())]
