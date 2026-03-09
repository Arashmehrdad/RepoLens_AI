from pydantic import BaseModel


class QuestionRequest(BaseModel):
    query: str
    collection_name: str = "repo_chunks"
    mode: str = "onboarding"


class QuestionResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence: str


class IngestRequest(BaseModel):
    repo_url: str


class IngestResponse(BaseModel):
    repo_path: str
    collection_name: str
    file_count: int
    document_count: int
    chunk_count: int
    indexed_count: int