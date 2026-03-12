"""Citation formatting helpers."""

MAX_CITATIONS = 3


def has_line_citation_metadata(metadata: dict) -> bool:
    """Return True when chunk metadata can support a line-aware citation."""
    path = metadata.get("path")
    start_line = metadata.get("start_line")
    end_line = metadata.get("end_line")

    return (
        bool(path)
        and isinstance(start_line, int)
        and isinstance(end_line, int)
        and 0 < start_line <= end_line
    )


def format_line_citation(metadata: dict) -> str:
    """Render a single metadata object as a line-aware citation string."""
    path = metadata["path"]
    start_line = metadata["start_line"]
    end_line = metadata["end_line"]

    if start_line == end_line:
        return f"{path}:{start_line}"

    return f"{path}:{start_line}-{end_line}"


def select_citation_chunks(
    retrieved_chunks: list[dict],
    max_citations: int = MAX_CITATIONS,
) -> list[dict]:
    """Select up to the best unique chunks that have valid citation spans."""
    selected_chunks = []
    seen_citations = set()

    for item in retrieved_chunks:
        metadata = item.get("metadata", {})
        if not has_line_citation_metadata(metadata):
            continue

        citation = format_line_citation(metadata)
        if citation in seen_citations:
            continue

        seen_citations.add(citation)
        selected_chunks.append(item)

        if len(selected_chunks) >= max_citations:
            break

    return selected_chunks


def format_citations(
    retrieved_chunks: list[dict],
    max_citations: int = MAX_CITATIONS,
) -> list[str]:
    """Format up to three unique line-aware citations from retrieved results."""
    citations = []

    for item in select_citation_chunks(retrieved_chunks, max_citations=max_citations):
        citations.append(format_line_citation(item["metadata"]))

    return citations
