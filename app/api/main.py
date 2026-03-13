"""FastAPI application for RepoLens AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.api.schemas import (
    IngestRequest,
    IngestResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.core.errors import IngestionLimitError
from app.core.env import load_environment
from app.core.setup import ensure_directories
from app.generation.answer_service import answer_question
from app.ingestion.pipeline import ingest_repository, resolve_collection_name
from app.ingestion.repo_manager import RepositoryCloneError


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize environment variables and required directories on startup."""
    del fastapi_app
    load_environment()
    ensure_directories()
    yield


app = FastAPI(title="RepoLens AI", version="0.5.0", lifespan=lifespan)


def _build_http_error(status_code: int, error) -> HTTPException:
    """Convert an application error into a structured HTTP exception."""
    return HTTPException(
        status_code=status_code,
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
    """Ingest a repository and return indexing summary data."""
    try:
        result = ingest_repository(request.repo_url)
    except IngestionLimitError as exc:
        raise _build_http_error(422, exc) from exc
    except RepositoryCloneError as exc:
        raise _build_http_error(503, exc) from exc

    return IngestResponse(
        repo_path=result["repo_path"],
        collection_name=result["collection_name"],
        file_count=result["file_count"],
        document_count=result["document_count"],
        chunk_count=result["chunk_count"],
        indexed_count=result["indexed_count"],
        ingestion_diagnostics=result.get("ingestion_diagnostics"),
    )


@app.post("/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest) -> QuestionResponse:
    """Answer a repository question using retrieved evidence."""
    try:
        collection_name = resolve_collection_name(
            repo_url=request.repo_url,
            collection_name=request.collection_name,
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
