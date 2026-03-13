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
                "is_readme": True,
            },
        },
        {
            "content": "api usage",
            "metadata": {
                "path": "README.md",
                "chunk_index": 1,
                "start_line": 40,
                "end_line": 52,
                "is_readme": True,
            },
        },
        {
            "content": "duplicate setup steps",
            "metadata": {
                "path": "README.md",
                "chunk_index": 0,
                "start_line": 12,
                "end_line": 28,
                "is_readme": True,
            },
        },
    ]

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)

    assert len(cleaned_chunks) == 2
    assert cleaned_chunks[0]["metadata"]["start_line"] == 12
    assert cleaned_chunks[1]["metadata"]["start_line"] == 40


def test_clean_retrieved_chunks_excludes_tests_by_default():
    """Test files should stay hidden unless the query explicitly targets debugging/testing."""
    retrieved_chunks = [
        {
            "content": "unit test details",
            "metadata": {"path": "tests/test_api.py", "chunk_index": 0},
        },
        {
            "content": "runtime behavior",
            "metadata": {"path": "app/api/main.py", "chunk_index": 0},
        },
    ]

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)

    assert len(cleaned_chunks) == 1
    assert cleaned_chunks[0]["metadata"]["path"] == "app/api/main.py"


def test_clean_retrieved_chunks_allows_tests_for_debug_queries():
    """Debug and testing queries should be allowed to surface test evidence."""
    retrieved_chunks = [
        {
            "content": "unit test details",
            "metadata": {"path": "tests/test_api.py", "chunk_index": 0, "is_test_file": True},
        },
        {
            "content": "runtime behavior",
            "metadata": {"path": "app/api/main.py", "chunk_index": 0},
        },
    ]

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks, query_intents={"debug"})

    assert len(cleaned_chunks) == 2


def test_clean_retrieved_chunks_filters_examples_by_default():
    """Example files should stay hidden unless the query intent suggests they matter."""
    retrieved_chunks = [
        {
            "content": "example usage",
            "metadata": {"path": "examples/demo.py", "chunk_index": 0, "is_example_file": True},
        },
        {
            "content": "real api code",
            "metadata": {"path": "app/api/main.py", "chunk_index": 0},
        },
    ]

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)

    assert len(cleaned_chunks) == 1
    assert cleaned_chunks[0]["metadata"]["path"] == "app/api/main.py"


def test_clean_retrieved_chunks_can_return_diagnostics():
    """Post-processing diagnostics should report dropped chunk categories."""
    retrieved_chunks = [
        {
            "content": "example usage",
            "metadata": {"path": "examples/demo.py", "chunk_index": 0, "is_example_file": True},
        },
        {
            "content": "runtime behavior",
            "metadata": {"path": "app/api/main.py", "chunk_index": 0},
        },
    ]

    cleaned_chunks, diagnostics = clean_retrieved_chunks(
        retrieved_chunks,
        return_diagnostics=True,
    )

    assert len(cleaned_chunks) == 1
    assert diagnostics["dropped_example_files"] == 1
    assert diagnostics["output_count"] == 1
