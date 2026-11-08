"""Parser plugins: PDF, DOCX, HTML, Markdown."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from docx import Document

from app.core.exceptions import IngestionError
from app.core.registry import PluginRegistry


@runtime_checkable
class ParserPlugin(Protocol):
    def parse(self, file_path: Path, **kwargs: Any) -> str: ...


class _BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path, **kwargs: Any) -> str:
        raise NotImplementedError


parser_registry: PluginRegistry[ParserPlugin] = PluginRegistry()


@parser_registry.register("pdf")
class PDFParser(_BaseParser):
    """Extract plain text from PDF via PyMuPDF."""

    def parse(self, file_path: Path, **kwargs: Any) -> str:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise IngestionError(f"Failed to open PDF: {e}") from e
        parts: list[str] = []
        try:
            for page in doc:
                parts.append(page.get_text("text"))
        finally:
            doc.close()
        return "\n\n".join(p.strip() for p in parts if p.strip())


@parser_registry.register("docx")
class DOCXParser(_BaseParser):
    """Extract paragraphs from Word documents."""

    def parse(self, file_path: Path, **kwargs: Any) -> str:
        try:
            document = Document(str(file_path))
        except Exception as e:
            raise IngestionError(f"Failed to open DOCX: {e}") from e
        return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())


@parser_registry.register("html")
class HTMLParser(_BaseParser):
    """Strip tags and normalize whitespace."""

    def parse(self, file_path: Path, **kwargs: Any) -> str:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = (ln.strip() for ln in text.splitlines())
        return "\n".join(ln for ln in lines if ln)


@parser_registry.register("markdown")
class MarkdownParser(_BaseParser):
    """Lightweight markdown: strip code fences and heading markers for plain text."""

    def parse(self, file_path: Path, **kwargs: Any) -> str:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"`[^`]+`", " ", text)
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        return text.strip()


def build_parser(name: str, **kwargs: Any) -> ParserPlugin:
    """Resolve parser plugin by name."""
    cls_or_factory = parser_registry.resolve(name)
    if isinstance(cls_or_factory, type):
        return cls_or_factory(**kwargs)  # type: ignore[misc]
    return cls_or_factory(**kwargs)  # type: ignore[operator]
