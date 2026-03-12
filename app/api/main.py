"""FastAPI application for RepoLens AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.api.schemas import (
    IngestRequest,
    IngestResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.core.env import load_environment
from app.core.setup import ensure_directories
from app.generation.answer_service import AnswerServiceUnavailableError, answer_question
from app.ingestion.pipeline import ingest_repository
from app.ingestion.repo_manager import RepositoryCloneError


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize environment variables and required directories on startup."""
    del fastapi_app
    load_environment()
    ensure_directories()
    yield


app = FastAPI(title="RepoLens AI", version="0.4.0", lifespan=lifespan)


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
    except RepositoryCloneError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return IngestResponse(
        repo_path=result["repo_path"],
        collection_name=result["collection_name"],
        file_count=result["file_count"],
        document_count=result["document_count"],
        chunk_count=result["chunk_count"],
        indexed_count=result["indexed_count"],
    )


@app.post("/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest) -> QuestionResponse:
    """Answer a repository question using retrieved evidence."""
    try:
        result = answer_question(
            query=request.query,
            collection_name=request.collection_name,
            mode=request.mode,
        )
    except AnswerServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return QuestionResponse(
        answer=result["answer"],
        citations=result["citations"],
        confidence=result["confidence"],
        trace_summary=result.get("trace_summary"),
    )
