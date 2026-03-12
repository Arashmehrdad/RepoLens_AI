"""Tests for citation formatting."""

from app.generation.citations import format_citations


def test_format_citations_outputs_line_ranges_and_deduplicates():
    """Duplicate line spans should only appear once in the citation list."""
    retrieved_chunks = [
        {"metadata": {"path": "README.md", "start_line": 12, "end_line": 28}},
        {"metadata": {"path": "README.md", "start_line": 12, "end_line": 28}},
        {"metadata": {"path": "app/api/main.py", "start_line": 5, "end_line": 31}},
    ]

    citations = format_citations(retrieved_chunks)

    assert citations == ["README.md:12-28", "app/api/main.py:5-31"]


def test_format_citations_uses_single_line_format_and_limits_results():
    """Single-line spans should use file:line and output should be capped at three items."""
    retrieved_chunks = [
        {"metadata": {"path": "requirements.txt", "start_line": 1, "end_line": 1}},
        {"metadata": {"path": "README.md", "start_line": 12, "end_line": 28}},
        {"metadata": {"path": "app/api/main.py", "start_line": 5, "end_line": 31}},
        {"metadata": {"path": "pyproject.toml", "start_line": 1, "end_line": 20}},
    ]

    citations = format_citations(retrieved_chunks)

    assert citations == [
        "requirements.txt:1",
        "README.md:12-28",
        "app/api/main.py:5-31",
    ]
