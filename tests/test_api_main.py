"""Tests for API response compatibility."""

from fastapi.testclient import TestClient

from app.api import main as api_main
from app.core.errors import IngestionLimitError
from app.ingestion.pipeline import build_collection_name


def test_ask_endpoint_preserves_existing_response_fields(monkeypatch):
    """The ask endpoint should keep answer/citations/confidence while adding trace data."""
    monkeypatch.setattr(
        api_main,
        "answer_question",
        lambda query, collection_name="repo_chunks", mode="onboarding": {
            "answer": "Use uvicorn.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "outcome": "answered",
            "error_code": None,
            "error_message": None,
            "retrieval_diagnostics": {"matched_intents": ["setup"]},
            "trace_summary": {
                "timestamp": "2026-03-12T12:00:00+00:00",
                "request_id": "req-123",
                "collection_name": "repo_chunks",
                "outcome": "answered",
                "confidence": "high",
                "error_code": None,
                "error_message": None,
                "request_latency_ms": 12.5,
                "retrieval_latency_ms": 4.1,
                "chunks_retrieved_count": 5,
                "chunks_after_cleaning_count": 3,
                "citations_count": 1,
                "top_paths": ["README.md"],
                "top_citations": ["README.md:12-28"],
                "query_intents": ["setup"],
                "retrieval_fetch_count": 12,
                "raw_results_count": 5,
            },
        },
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/ask",
            json={
                "query": "How do I run this project?",
                "collection_name": "repo_chunks",
                "mode": "onboarding",
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["answer"] == "Use uvicorn."
    assert payload["citations"] == ["README.md:12-28"]
    assert payload["confidence"] == "high"
    assert payload["outcome"] == "answered"
    assert payload["trace_summary"]["request_id"] == "req-123"
    assert payload["retrieval_diagnostics"]["matched_intents"] == ["setup"]


def test_health_endpoint_returns_ok():
    """The deployment health endpoint should return an OK status."""
    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_endpoint_returns_structured_limit_errors(monkeypatch):
    """Ingest failures should surface structured error codes and messages."""
    monkeypatch.setattr(
        api_main,
        "ingest_repository",
        lambda repo_url: (_ for _ in ()).throw(
            IngestionLimitError(
                "too many files",
                error_code="ingestion_no_supported_files",
                diagnostics={"selected_files": 0},
            )
        ),
    )

    with TestClient(api_main.app) as client:
        response = client.post("/ingest", json={"repo_url": "https://github.com/example/demo"})

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "ingestion_no_supported_files"
    assert response.json()["detail"]["error_message"] == "too many files"


def test_ingest_and_ask_use_the_same_repo_specific_collection(monkeypatch):
    """Ask should resolve the same normalized collection name created during ingest."""
    repo_url = "https://github.com/Arashmehrdad/RepoLens_AI.git/"
    expected_collection_name = build_collection_name(repo_url)
    observed_collections = []

    monkeypatch.setattr(
        api_main,
        "ingest_repository",
        lambda incoming_repo_url: {
            "repo_path": "D:/tmp/RepoLens_AI",
            "collection_name": build_collection_name(incoming_repo_url),
            "file_count": 10,
            "document_count": 9,
            "chunk_count": 18,
            "indexed_count": 18,
        },
    )

    def fake_answer_question(query, collection_name, mode="onboarding"):
        observed_collections.append(collection_name)
        assert collection_name == expected_collection_name
        return {
            "answer": "Use docker compose up --build.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "outcome": "answered",
            "error_code": None,
            "error_message": None,
            "retrieval_diagnostics": {"matched_intents": ["setup"], "raw_result_count": 3},
            "trace_summary": {
                "timestamp": "2026-03-12T12:00:00+00:00",
                "request_id": "req-456",
                "collection_name": expected_collection_name,
                "outcome": "answered",
                "confidence": "high",
                "error_code": None,
                "error_message": None,
                "request_latency_ms": 10.0,
                "retrieval_latency_ms": 3.5,
                "chunks_retrieved_count": 3,
                "chunks_after_cleaning_count": 2,
                "citations_count": 1,
                "top_paths": ["README.md"],
                "top_citations": ["README.md:12-28"],
                "query_intents": ["setup"],
                "retrieval_fetch_count": 12,
                "raw_results_count": 3,
            },
        }

    monkeypatch.setattr(api_main, "answer_question", fake_answer_question)

    with TestClient(api_main.app) as client:
        ingest_response = client.post("/ingest", json={"repo_url": repo_url})
        ask_response = client.post(
            "/ask",
            json={
                "query": "How do I run this project?",
                "repo_url": repo_url,
                "mode": "onboarding",
            },
        )

    assert ingest_response.status_code == 200
    assert ingest_response.json()["collection_name"] == expected_collection_name
    assert ask_response.status_code == 200
    assert observed_collections == [expected_collection_name]
    assert ask_response.json()["trace_summary"]["raw_results_count"] == 3
