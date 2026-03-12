"""Tests for retrieval post-processing."""

from app.retrieval.postprocess import clean_retrieved_chunks


def test_clean_retrieved_chunks_preserves_multiple_spans_from_same_file():
    """Different spans from the same file should survive post-processing."""
    retrieved_chunks = [
        {
            "content": "setup steps",
            "metadata": {
                "path": "README.md",
                "chunk_index": 0,
                "start_line": 12,
                "end_line": 28,
            },
        },
        {
            "content": "api usage",
            "metadata": {
                "path": "README.md",
                "chunk_index": 1,
                "start_line": 40,
                "end_line": 52,
            },
        },
        {
            "content": "duplicate setup steps",
            "metadata": {
                "path": "README.md",
                "chunk_index": 0,
                "start_line": 12,
                "end_line": 28,
            },
        },
    ]

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)

    assert len(cleaned_chunks) == 2
    assert cleaned_chunks[0]["metadata"]["start_line"] == 12
    assert cleaned_chunks[1]["metadata"]["start_line"] == 40
