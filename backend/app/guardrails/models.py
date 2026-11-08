"""Shared guardrail DTOs."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GuardrailAction(str, Enum):
    REDACT = "redact"
    BLOCK = "block"
    WARN = "warn"


class GuardrailResult(BaseModel):
    text: str
    blocked: bool = False
    warnings: list[str] = Field(default_factory=list)
    redacted_fields: list[str] = Field(default_factory=list)
