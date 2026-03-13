"""Tests for trace payload structure."""

from app.generation import answer_service


def test_answer_service_trace_payload_includes_latency_and_counts(monkeypatch):
    """Ask traces should record latencies, counts, and retrieval diagnostics."""
    cleaned_chunks = [
        {
            "content": "Run the app with uvicorn.",
            "metadata": {
                "path": "README.md",
                "chunk_index": 0,
                "start_line": 12,
                "end_line": 28,
            },
            "distance": 0.1,
        }
    ]
    captured_traces = []

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
        lambda chunks, query_intents=None, return_diagnostics=False: (
            (chunks, {"input_count": 1, "output_count": 1})
            if return_diagnostics
            else chunks
        ),
    )
    monkeypatch.setattr(answer_service, "write_grounded_answer", lambda query, retrieved_chunks, mode="onboarding": "Use uvicorn.")
    monkeypatch.setattr(
        answer_service,
        "log_trace",
        lambda payload: captured_traces.append(payload) or {"timestamp": "2026-03-12T12:00:00+00:00", **payload},
    )

    result = answer_service.answer_question(
        "How do I run this project?",
        collection_name="repo_repolens_ai",
    )
    trace_payload = captured_traces[0]

    assert result["trace_summary"]["request_id"]
    assert trace_payload["collection_name"] == "repo_repolens_ai"
    assert isinstance(trace_payload["request_latency_ms"], float)
    assert isinstance(trace_payload["retrieval_latency_ms"], float)
    assert trace_payload["chunks_retrieved_count"] == 1
    assert trace_payload["chunks_after_cleaning_count"] == 1
    assert trace_payload["citations_count"] == 1
    assert trace_payload["outcome"] == "answered"
    assert trace_payload["error_code"] is None
    assert trace_payload["retrieval_diagnostics"]["matched_intents"] == ["setup"]
