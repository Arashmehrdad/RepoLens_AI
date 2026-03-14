"""Pydantic request and response models for the API."""

# pylint: disable=duplicate-code

from pydantic import BaseModel, Field


class RepoStateModel(BaseModel):
    """Serializable description of one ingested repository state."""

    repo_url: str
    repo_name: str
    normalized_repo_url: str
    ref: str
    state_id: str
    collection_name: str
    repo_path: str | None = None
    commit_sha: str | None = None
    manifest_path: str | None = None


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
    ref: str | None = None
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
    ref: str | None = None


class IngestResponse(BaseModel):
    """Summary returned after repository ingestion completes."""

    repo_path: str
    collection_name: str
    file_count: int
    document_count: int
    chunk_count: int
    indexed_count: int
    ingestion_diagnostics: dict | None = None
    state: RepoStateModel | None = None
    manifest_path: str | None = None
    incremental_stats: dict | None = None


class CompareRequest(BaseModel):
    """Payload for comparing two repository states."""

    repo_url_a: str
    repo_url_b: str
    ref_a: str | None = None
    ref_b: str | None = None
    query: str | None = None
    mode: str = "compare"


class CompareResponse(BaseModel):
    """Grounded multi-repo comparison response."""

    answer: str
    citations: list[str]
    confidence: str
    outcome: str
    error_code: str | None = None
    error_message: str | None = None
    state_a: RepoStateModel | None = None
    state_b: RepoStateModel | None = None
    changed_files: list[str] = Field(default_factory=list)
    added_files: list[str] = Field(default_factory=list)
    removed_files: list[str] = Field(default_factory=list)
    setup_impact: list[str] = Field(default_factory=list)
    deployment_impact: list[str] = Field(default_factory=list)
    ci_cd_impact: list[str] = Field(default_factory=list)
    package_impact: list[str] = Field(default_factory=list)
    api_runtime_impact: list[str] = Field(default_factory=list)
    diagnostics: dict | None = None
    state_a_citations: list[str] = Field(default_factory=list)
    state_b_citations: list[str] = Field(default_factory=list)
    state_a_evidence: list[dict] = Field(default_factory=list)
    state_b_evidence: list[dict] = Field(default_factory=list)


class RegressionResponse(BaseModel):
    """Structured regression dashboard response."""

    available_versions: list[str] = Field(default_factory=list)
    selected_versions: list[str] = Field(default_factory=list)
    versions: list[dict] = Field(default_factory=list)
    runs: list[dict] = Field(default_factory=list)
    metric_series: list[dict] = Field(default_factory=list)


class ReviewReportRequest(BaseModel):
    """Payload for generating an exportable compare review report."""

    repo_url_a: str
    repo_url_b: str
    ref_a: str | None = None
    ref_b: str | None = None
    query: str | None = None
    mode: str = "compare"


class ReviewReportResponse(BaseModel):
    """Response returned after exporting a compare review report."""

    report_id: str
    mode: str
    json_path: str
    markdown_path: str
    markdown: str
    report: dict
