"""Application state wired in ``lifespan`` and read from ``request.app.state``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import redis.asyncio as redis
from opensearchpy import OpenSearch

from app.cache.semantic_cache import SemanticCache
from app.core.config import Settings, YamlAppConfig
from app.core.llm import LLMProvider
from app.evaluation.metrics import EvaluationEngine
from app.generation.generator import GenerationEngine
from app.guardrails.chain import GuardrailChain
from app.ingestion.pipeline import IngestionPipeline
from app.observability.event_bus import EventBus
from app.observability.langfuse_tracer import LangfuseTracer
from app.retrieval.engine import RetrievalEngine
from app.storage.collections import CollectionStore
from app.storage.documents import DocumentStore


@dataclass
class AppState:
    settings: Settings
    yaml_config: YamlAppConfig
    opensearch: OpenSearch
    redis: redis.Redis
    llm: LLMProvider
    ingestion: IngestionPipeline
    retrieval: RetrievalEngine
    generation: GenerationEngine
    input_guardrails: GuardrailChain
    output_guardrails: GuardrailChain
    evaluation: EvaluationEngine
    semantic_cache: SemanticCache
    event_bus: EventBus
    langfuse: LangfuseTracer
    documents: DocumentStore
    collections: CollectionStore
    uploads_path: Path = field(default_factory=Path)
    reindex_requested: bool = False
