"""Tests for API response compatibility."""

from fastapi.testclient import TestClient

from app.api import main as api_main
from app.generation.answer_service import AnswerServiceUnavailableError


def test_ask_endpoint_preserves_existing_response_fields(monkeypatch):
    """The ask endpoint should keep answer/citations/confidence while adding trace data."""
    monkeypatch.setattr(
        api_main,
        "answer_question",
        lambda query, collection_name="repo_chunks", mode="onboarding": {
            "answer": "Use uvicorn.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "trace_summary": {
                "timestamp": "2026-03-12T12:00:00+00:00",
                "request_id": "req-123",
                "outcome": "answered",
                "confidence": "high",
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
    assert payload["trace_summary"]["request_id"] == "req-123"


def test_health_endpoint_returns_ok():
    """The deployment health endpoint should return an OK status."""
    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_endpoint_returns_503_for_unavailable_answer_service(monkeypatch):
    """The ask endpoint should return a clean 503 for retrieval dependency failures."""
    monkeypatch.setattr(
        api_main,
        "answer_question",
        lambda query, collection_name="repo_chunks", mode="onboarding": (_ for _ in ()).throw(
            AnswerServiceUnavailableError("service unavailable")
        ),
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

    assert response.status_code == 503
    assert response.json()["detail"] == "service unavailable"
