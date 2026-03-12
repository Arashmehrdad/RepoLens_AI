"""Pydantic request and response models for the API."""

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    """Payload for asking a question against an indexed repository."""

    query: str
    collection_name: str = "repo_chunks"
    mode: str = "onboarding"


class QuestionResponse(BaseModel):
    """Response returned for repository question answering."""

    answer: str
    citations: list[str]
    confidence: str


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
