"""Tests for the evidence gate."""

from app.guardrails.evidence_gate import has_enough_evidence


def test_has_enough_evidence_returns_true_for_strong_chunk():
    """A nearby retrieved chunk should satisfy the evidence threshold."""
    retrieved_chunks = [
        {
            "distance": 0.2,
            "metadata": {"path": "README.md", "start_line": 12, "end_line": 28},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is True


def test_has_enough_evidence_returns_false_for_distant_chunks():
    """Chunks outside the distance threshold should not count as sufficient evidence."""
    retrieved_chunks = [
        {
            "distance": 2.0,
            "metadata": {"path": "README.md", "start_line": 12, "end_line": 28},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is False


def test_has_enough_evidence_requires_line_metadata():
    """Strong chunks without line spans should not pass the evidence gate."""
    retrieved_chunks = [
        {
            "distance": 0.2,
            "metadata": {"path": "README.md"},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is False


def test_has_enough_evidence_allows_strong_reranked_borderline_chunk():
    """Borderline semantic matches can pass when reranking is strong and cited."""
    retrieved_chunks = [
        {
            "distance": 1.7,
            "rerank_score": 5.2,
            "metadata": {"path": "app/ui/home.py", "start_line": 1, "end_line": 20},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is True
