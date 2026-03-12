"""Tests for the answer service."""

from app.generation import answer_service


def test_answer_question_refuses_when_citation_metadata_is_missing(monkeypatch):
    """Answers should refuse when strong evidence lacks valid line-aware citations."""
    cleaned_chunks = [
        {
            "content": "weak evidence",
            "metadata": {"path": "README.md", "chunk_index": 0},
            "distance": 0.2,
        }
    ]
    traces = []

    monkeypatch.setattr(
        answer_service,
        "retrieve_chunks",
        lambda query, collection_name="repo_chunks", n_results=5, mode=None, return_diagnostics=False: (
            (cleaned_chunks, {"matched_intents": ["setup"], "fetch_count": 12, "raw_result_count": 1})
            if return_diagnostics
            else cleaned_chunks
        ),
    )
    monkeypatch.setattr(
        answer_service,
        "clean_retrieved_chunks",
        lambda chunks, query_intents=None: chunks,
    )
    monkeypatch.setattr(answer_service, "log_trace", lambda payload: traces.append(payload) or payload)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("write_grounded_answer should not run for refusal cases")

    monkeypatch.setattr(answer_service, "write_grounded_answer", fail_if_called)

    result = answer_service.answer_question("What is the capital of France?")

    assert result["confidence"] == "low"
    assert result["citations"] == []
    assert "I do not have enough evidence" in result["answer"]
    assert result["trace_summary"]["outcome"] == "refused"
    assert traces[0]["confidence"] == "low"


def test_answer_question_returns_line_aware_citations(monkeypatch):
    """Strong evidence should produce one to three line-aware citations."""
    cleaned_chunks = [
        {
            "content": "Run `uvicorn app.api.main:app` from the project root.",
            "metadata": {"path": "README.md", "chunk_index": 0, "start_line": 12, "end_line": 28},
            "distance": 0.1,
        },
        {
            "content": "Install dependencies from requirements.txt.",
            "metadata": {"path": "requirements.txt", "chunk_index": 1, "start_line": 1, "end_line": 10},
            "distance": 0.2,
        },
        {
            "content": "FastAPI app entry point.",
            "metadata": {"path": "app/api/main.py", "chunk_index": 2, "start_line": 5, "end_line": 31},
            "distance": 0.3,
        },
        {
            "content": "Extra evidence that should not be cited.",
            "metadata": {"path": "pyproject.toml", "chunk_index": 3, "start_line": 1, "end_line": 20},
            "distance": 0.4,
        },
    ]
    traces = []
    captured = {}

    monkeypatch.setattr(
        answer_service,
        "retrieve_chunks",
        lambda query, collection_name="repo_chunks", n_results=5, mode=None, return_diagnostics=False: (
            (cleaned_chunks, {"matched_intents": ["setup"], "fetch_count": 12, "raw_result_count": 4})
            if return_diagnostics
            else cleaned_chunks
        ),
    )
    monkeypatch.setattr(
        answer_service,
        "clean_retrieved_chunks",
        lambda chunks, query_intents=None: chunks,
    )
    monkeypatch.setattr(answer_service, "log_trace", lambda payload: traces.append(payload) or payload)

    def fake_write_grounded_answer(query, retrieved_chunks, mode="onboarding"):
        captured["chunks"] = retrieved_chunks
        return "Use uvicorn."

    monkeypatch.setattr(answer_service, "write_grounded_answer", fake_write_grounded_answer)

    result = answer_service.answer_question("How do I run this project?")

    assert result["answer"] == "Use uvicorn."
    assert result["citations"] == [
        "README.md:12-28",
        "requirements.txt:1-10",
        "app/api/main.py:5-31",
    ]
    assert result["confidence"] == "high"
    assert len(result["citations"]) == 3
    assert len(captured["chunks"]) == 3
    assert result["trace_summary"]["outcome"] == "answered"
    assert result["trace_summary"]["query_intents"] == ["setup"]
    assert traces[0]["citations"] == [
        "README.md:12-28",
        "requirements.txt:1-10",
        "app/api/main.py:5-31",
    ]


def test_answer_question_raises_clean_error_when_retrieval_is_unavailable(monkeypatch):
    """Retrieval dependency failures should surface as a clear service error."""

    def fail_retrieval(**kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(answer_service, "retrieve_chunks", fail_retrieval)

    try:
        answer_service.answer_question("How do I run this project?")
    except answer_service.AnswerServiceUnavailableError as exc:
        assert "ready vector index" in str(exc)
    else:
        raise AssertionError("Expected AnswerServiceUnavailableError to be raised")
