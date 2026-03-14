"""FastAPI application for RepoLens AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.api.schemas import (
    CompareRequest,
    CompareResponse,
    IngestRequest,
    IngestResponse,
    QuestionRequest,
    QuestionResponse,
    RegressionResponse,
    ReviewReportRequest,
    ReviewReportResponse,
)
from app.comparison.service import compare_repo_states
from app.core.env import load_environment
from app.core.errors import (
    ComparisonError,
    IngestionLimitError,
    RegressionError,
    ReportGenerationError,
    RepoLensError,
    RepoStateError,
    VectorStoreError,
)
from app.core.setup import ensure_directories
from app.evals.regressions import aggregate_regressions
from app.generation.answer_service import answer_question
from app.ingestion.pipeline import (
    ingest_repository,
    ingest_repository_state,
    resolve_collection_name,
)
from app.ingestion.repo_manager import RepositoryCloneError
from app.reports.review_report import export_review_report


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize environment variables and required directories on startup."""
    del fastapi_app
    load_environment()
    ensure_directories()
    yield


app = FastAPI(title="RepoLens AI", version="0.6.0", lifespan=lifespan)


def _error_status_code(error: RepoLensError) -> int:
    """Return the HTTP status code appropriate for one app error."""
    if isinstance(error, (RepositoryCloneError, VectorStoreError)):
        return 503

    if isinstance(
        error,
        (
            IngestionLimitError,
            RepoStateError,
            ComparisonError,
            RegressionError,
            ReportGenerationError,
        ),
    ):
        return 422

    return 500


def _build_http_error(error: RepoLensError) -> HTTPException:
    """Convert an application error into a structured HTTP exception."""
    return HTTPException(
        status_code=_error_status_code(error),
        detail={
            "error_code": error.error_code,
            "error_message": str(error),
            "diagnostics": error.diagnostics,
        },
    )


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a basic health response."""
    return {"message": "RepoLens AI is running"}


@app.get("/health")
def read_health() -> dict[str, str]:
    """Return a compact deployment health response."""
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_repo(request: IngestRequest) -> IngestResponse:
    """Ingest one repository state and return indexing summary data."""
    try:
        if request.ref:
            result = ingest_repository_state(request.repo_url, ref=request.ref)
        else:
            result = ingest_repository(request.repo_url)
    except RepoLensError as exc:
        raise _build_http_error(exc) from exc

    return IngestResponse(
        repo_path=result["repo_path"],
        collection_name=result["collection_name"],
        file_count=result["file_count"],
        document_count=result["document_count"],
        chunk_count=result["chunk_count"],
        indexed_count=result["indexed_count"],
        ingestion_diagnostics=result.get("ingestion_diagnostics"),
        state=result.get("state"),
        manifest_path=result.get("manifest_path"),
        incremental_stats=result.get("incremental_stats"),
    )


@app.post("/ask", response_model=QuestionResponse)
def ask_question_endpoint(request: QuestionRequest) -> QuestionResponse:
    """Answer a repository question using retrieved evidence."""
    try:
        collection_name = resolve_collection_name(
            repo_url=request.repo_url,
            collection_name=request.collection_name,
            ref=request.ref,
        )
        result = answer_question(
            query=request.query,
            collection_name=collection_name,
            mode=request.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return QuestionResponse(
        answer=result["answer"],
        citations=result["citations"],
        confidence=result["confidence"],
        outcome=result["outcome"],
        error_code=result.get("error_code"),
        error_message=result.get("error_message"),
        trace_summary=result.get("trace_summary"),
        retrieval_diagnostics=result.get("retrieval_diagnostics"),
    )


def _build_compare_response(result: dict) -> CompareResponse:
    """Convert a compare result dictionary into the response model."""
    return CompareResponse(
        answer=result["answer"],
        citations=result["citations"],
        confidence=result["confidence"],
        outcome=result["outcome"],
        error_code=result.get("error_code"),
        error_message=result.get("error_message"),
        state_a=result.get("state_a"),
        state_b=result.get("state_b"),
        changed_files=result.get("changed_files", []),
        added_files=result.get("added_files", []),
        removed_files=result.get("removed_files", []),
        setup_impact=result.get("setup_impact", []),
        deployment_impact=result.get("deployment_impact", []),
        ci_cd_impact=result.get("ci_cd_impact", []),
        package_impact=result.get("package_impact", []),
        api_runtime_impact=result.get("api_runtime_impact", []),
        diagnostics=result.get("diagnostics"),
        state_a_citations=result.get("state_a_citations", []),
        state_b_citations=result.get("state_b_citations", []),
        state_a_evidence=result.get("state_a_evidence", []),
        state_b_evidence=result.get("state_b_evidence", []),
    )


@app.post("/compare", response_model=CompareResponse)
def compare_repositories(request: CompareRequest) -> CompareResponse:
    """Compare two repository states and return grounded change diagnostics."""
    try:
        result = compare_repo_states(
            repo_url_a=request.repo_url_a,
            repo_url_b=request.repo_url_b,
            ref_a=request.ref_a,
            ref_b=request.ref_b,
            query=request.query,
            mode=request.mode,
        )
    except RepoLensError as exc:
        raise _build_http_error(exc) from exc

    return _build_compare_response(result)


@app.post("/release-diff", response_model=CompareResponse)
def compare_release_states(request: CompareRequest) -> CompareResponse:
    """Compare two repository states using release-diff prioritization."""
    try:
        result = compare_repo_states(
            repo_url_a=request.repo_url_a,
            repo_url_b=request.repo_url_b,
            ref_a=request.ref_a,
            ref_b=request.ref_b,
            query=request.query,
            mode="release_diff",
        )
    except RepoLensError as exc:
        raise _build_http_error(exc) from exc

    return _build_compare_response(result)


@app.get("/eval-regressions", response_model=RegressionResponse)
def get_eval_regressions(
    versions: str | None = Query(
        default=None,
        description="Comma-separated eval version labels to include.",
    ),
) -> RegressionResponse:
    """Return aggregated eval regression data across saved result runs."""
    selected_versions = [
        version.strip()
        for version in (versions or "").split(",")
        if version.strip()
    ]
    try:
        result = aggregate_regressions(versions=selected_versions or None)
    except RepoLensError as exc:
        raise _build_http_error(exc) from exc

    return RegressionResponse(**result)


@app.post("/review-report", response_model=ReviewReportResponse)
def generate_review_report(request: ReviewReportRequest) -> ReviewReportResponse:
    """Generate and export a deterministic compare or release-diff report."""
    try:
        result = export_review_report(
            repo_url_a=request.repo_url_a,
            repo_url_b=request.repo_url_b,
            ref_a=request.ref_a,
            ref_b=request.ref_b,
            query=request.query,
            mode=request.mode,
        )
    except RepoLensError as exc:
        raise _build_http_error(exc) from exc

    return ReviewReportResponse(
        report_id=result["report_id"],
        mode=result["mode"],
        json_path=result["json_path"],
        markdown_path=result["markdown_path"],
        markdown=result["markdown"],
        report=result["report"],
    )
