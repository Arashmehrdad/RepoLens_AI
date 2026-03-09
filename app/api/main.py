from fastapi import FastAPI

from app.api.schemas import (
    IngestRequest,
    IngestResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.core.env import load_environment
from app.core.setup import ensure_directories
from app.generation.answer_service import answer_question
from app.ingestion.pipeline import ingest_repository

app = FastAPI(title="RepoLens AI")


@app.on_event("startup")
def startup_event() -> None:
    load_environment()
    ensure_directories()


@app.get("/")
def read_root():
    return {"message": "RepoLens AI is running"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_repo(request: IngestRequest):
    result = ingest_repository(request.repo_url)

    return IngestResponse(
        repo_path=result["repo_path"],
        collection_name=result["collection_name"],
        file_count=result["file_count"],
        document_count=result["document_count"],
        chunk_count=result["chunk_count"],
        indexed_count=result["indexed_count"],
    )


@app.post("/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest):
    result = answer_question(
        query=request.query,
        collection_name=request.collection_name,
        mode=request.mode,
    )

    return QuestionResponse(
        answer=result["answer"],
        citations=result["citations"],
        confidence=result["confidence"],
    )