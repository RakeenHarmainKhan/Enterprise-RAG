"""Nested pydantic models for YAML config and environment settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout_seconds: int = 120


class IngestionConfig(BaseModel):
    parser: str = "pdf"
    chunker: str = "recursive"
    embedder: str = "openai"
    indexer: str = "opensearch"
    parser_params: dict[str, Any] = Field(default_factory=dict)
    chunker_params: dict[str, Any] = Field(default_factory=dict)
    embedder_params: dict[str, Any] = Field(default_factory=dict)
    indexer_params: dict[str, Any] = Field(default_factory=dict)


class RetrievalStrategyItem(BaseModel):
    name: str
    weight: float = 1.0
    params: dict[str, Any] = Field(default_factory=dict)


class RetrievalConfig(BaseModel):
    router: str = "hybrid"
    strategies: list[RetrievalStrategyItem] = Field(default_factory=list)
    fusion: str = "rrf"
    fusion_params: dict[str, Any] = Field(default_factory=dict)
    reranker: str = "cross_encoder"
    reranker_params: dict[str, Any] = Field(default_factory=dict)


class GenerationConfig(BaseModel):
    context_window_tokens: int = 8000
    streaming: bool = True
    citation_style: Literal["bracket", "footnote", "none"] = "bracket"


class GuardrailStepConfig(BaseModel):
    plugin: str
    params: dict[str, Any] = Field(default_factory=dict)


class GuardrailsConfig(BaseModel):
    input_chain: list[GuardrailStepConfig] = Field(default_factory=list)
    output_chain: list[GuardrailStepConfig] = Field(default_factory=list)


class EvaluationConfig(BaseModel):
    metrics: list[str] = Field(
        default_factory=lambda: [
            "faithfulness",
            "answer_relevance",
            "context_precision",
            "context_recall",
        ]
    )


class CacheConfig(BaseModel):
    backend: str = "redis"
    ttl_seconds: int = 3600
    similarity_threshold: float = 0.92


class ObservabilityConfig(BaseModel):
    langfuse_enabled: bool = True
    tracing: bool = True


class YamlAppConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)


def load_yaml_config(path: str | Path) -> YamlAppConfig:
    """Parse ``config.yaml`` into structured models."""
    p = Path(path)
    if not p.is_file():
        return YamlAppConfig()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return YamlAppConfig.model_validate(raw)


class Settings(BaseSettings):
    """Environment-backed settings (secrets and deployment)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")

    opensearch_url: str = Field(default="http://localhost:9200", alias="OPENSEARCH_URL")
    opensearch_user: str | None = Field(default=None, alias="OPENSEARCH_USER")
    opensearch_password: str | None = Field(default=None, alias="OPENSEARCH_PASSWORD")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_base_url: str = Field(
        default="https://cloud.langfuse.com",
        alias="LANGFUSE_BASE_URL",
    )

    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    config_yaml_path: str = Field(default="config.yaml", alias="CONFIG_YAML_PATH")

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )
    debug: bool = Field(default=False, alias="DEBUG")

    uploads_dir: str = Field(default="uploads", alias="UPLOADS_DIR")
    logs_dir: str = Field(default="logs", alias="LOGS_DIR")

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def merge_llm_from_env(yaml_cfg: YamlAppConfig, settings: Settings) -> LLMConfig:
    """Apply env overrides to YAML LLM section."""
    llm = yaml_cfg.llm.model_copy()
    if settings.llm_model:
        llm.model = settings.llm_model
    if settings.llm_provider:
        llm.provider = settings.llm_provider
    return llm
