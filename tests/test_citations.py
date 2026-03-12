"""Tests for citation formatting."""

from app.generation.citations import format_citations


def test_format_citations_deduplicates_chunk_references():
    """Duplicate chunk references should only appear once in the citation list."""
    retrieved_chunks = [
        {"metadata": {"path": "README.md", "chunk_index": 0}},
        {"metadata": {"path": "README.md", "chunk_index": 0}},
        {"metadata": {"path": "app/api/main.py", "chunk_index": 1}},
    ]

    citations = format_citations(retrieved_chunks)

    assert citations == ["README.md [chunk 0]", "app/api/main.py [chunk 1]"]
