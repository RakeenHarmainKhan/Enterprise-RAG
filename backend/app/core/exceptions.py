"""Domain-specific exceptions for ingestion, retrieval, generation, guardrails, and evaluation."""


class EnterpriseRAGError(Exception):
    """Base error for the application domain."""


class IngestionError(EnterpriseRAGError):
    """Raised when document parsing, chunking, embedding, or indexing fails."""


class RetrievalError(EnterpriseRAGError):
    """Raised when routing, search, fusion, or reranking fails."""


class GenerationError(EnterpriseRAGError):
    """Raised when context assembly or LLM generation fails."""


class GuardrailError(EnterpriseRAGError):
    """Raised when a guardrail blocks processing or encounters a fatal condition."""


class EvaluationError(EnterpriseRAGError):
    """Raised when evaluation metrics cannot be computed."""
