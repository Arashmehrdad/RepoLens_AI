"""Tests for the answer service."""

from app.generation import answer_service


def test_answer_question_returns_refusal_when_evidence_is_weak(monkeypatch):
    """Weak evidence should produce a refusal response without calling the LLM."""
    cleaned_chunks = [
        {
            "content": "weak evidence",
            "metadata": {"path": "README.md", "chunk_index": 0},
            "distance": 2.0,
        }
    ]
    traces = []

    monkeypatch.setattr(
        answer_service,
        "retrieve_chunks",
        lambda query, collection_name="repo_chunks", n_results=5: cleaned_chunks,
    )
    monkeypatch.setattr(answer_service, "clean_retrieved_chunks", lambda chunks: chunks)
    monkeypatch.setattr(answer_service, "has_enough_evidence", lambda chunks: False)
    monkeypatch.setattr(answer_service, "log_trace", traces.append)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("write_grounded_answer should not run for refusal cases")

    monkeypatch.setattr(answer_service, "write_grounded_answer", fail_if_called)

    result = answer_service.answer_question("What is the capital of France?")

    assert result["confidence"] == "low"
    assert result["citations"] == []
    assert "I do not have enough evidence" in result["answer"]
    assert traces[0]["confidence"] == "low"


def test_answer_question_returns_grounded_answer(monkeypatch):
    """Strong evidence should produce an answer with citations and trace logging."""
    cleaned_chunks = [
        {
            "content": "Run `uvicorn app.api.main:app`",
            "metadata": {"path": "README.md", "chunk_index": 0},
            "distance": 0.1,
        }
    ]
    traces = []

    monkeypatch.setattr(
        answer_service,
        "retrieve_chunks",
        lambda query, collection_name="repo_chunks", n_results=5: cleaned_chunks,
    )
    monkeypatch.setattr(answer_service, "clean_retrieved_chunks", lambda chunks: chunks)
    monkeypatch.setattr(answer_service, "has_enough_evidence", lambda chunks: True)
    monkeypatch.setattr(answer_service, "write_grounded_answer", lambda **kwargs: "Use uvicorn.")
    monkeypatch.setattr(answer_service, "format_citations", lambda chunks: ["README.md [chunk 0]"])
    monkeypatch.setattr(answer_service, "log_trace", traces.append)

    result = answer_service.answer_question("How do I run this project?")

    assert result["answer"] == "Use uvicorn."
    assert result["citations"] == ["README.md [chunk 0]"]
    assert result["confidence"] == "high"
    assert traces[0]["citations"] == ["README.md [chunk 0]"]
