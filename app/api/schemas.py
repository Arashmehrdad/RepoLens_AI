"""Pydantic request and response models for the API."""

from pydantic import BaseModel, Field


class TraceSummary(BaseModel):
    """Compact observability summary for a single ask request."""

    timestamp: str | None = None
    request_id: str
    collection_name: str | None = None
    outcome: str
    confidence: str
    error_code: str | None = None
    error_message: str | None = None
    request_latency_ms: float
    retrieval_latency_ms: float
    chunks_retrieved_count: int
    chunks_after_cleaning_count: int
    citations_count: int
    top_paths: list[str] = Field(default_factory=list)
    top_citations: list[str] = Field(default_factory=list)
    query_intents: list[str] = Field(default_factory=list)
    retrieval_fetch_count: int | None = None
    raw_results_count: int | None = None


class QuestionRequest(BaseModel):
    """Payload for asking a question against an indexed repository."""

    query: str
    repo_url: str | None = None
    collection_name: str | None = None
    mode: str = "onboarding"


class QuestionResponse(BaseModel):
    """Response returned for repository question answering."""

    answer: str
    citations: list[str]
    confidence: str
    outcome: str
    error_code: str | None = None
    error_message: str | None = None
    trace_summary: TraceSummary | None = None
    retrieval_diagnostics: dict | None = None


class IngestRequest(BaseModel):
    """Payload for starting repository ingestion."""

    repo_url: str


class IngestResponse(BaseModel):
    """Summary returned after repository ingestion completes."""

    repo_path: str
    collection_name: str
    file_count: int
    document_count: int
    chunk_count: int
    indexed_count: int
    ingestion_diagnostics: dict | None = None
