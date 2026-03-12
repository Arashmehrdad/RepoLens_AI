"""Tests for the evidence gate."""

from app.guardrails.evidence_gate import has_enough_evidence


def test_has_enough_evidence_returns_true_for_strong_chunk():
    """A nearby retrieved chunk should satisfy the evidence threshold."""
    retrieved_chunks = [
        {
            "distance": 0.2,
            "metadata": {"path": "README.md"},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is True


def test_has_enough_evidence_returns_false_for_distant_chunks():
    """Chunks outside the distance threshold should not count as sufficient evidence."""
    retrieved_chunks = [
        {
            "distance": 2.0,
            "metadata": {"path": "README.md"},
        }
    ]

    assert has_enough_evidence(retrieved_chunks) is False
