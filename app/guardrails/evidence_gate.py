"""Evidence sufficiency checks for grounded answers."""


def _has_valid_line_span(metadata: dict) -> bool:
    """Return True when metadata contains a valid line-range citation."""
    start_line = metadata.get("start_line")
    end_line = metadata.get("end_line")

    return (
        bool(metadata.get("path"))
        and isinstance(start_line, int)
        and isinstance(end_line, int)
        and 0 < start_line <= end_line
    )


def has_enough_evidence(
    retrieved_chunks: list[dict],
    min_chunks: int = 1,
    max_distance: float = 1.5,
) -> bool:
    """Return True when retrieval results meet minimum evidence thresholds."""
    if len(retrieved_chunks) < min_chunks:
        return False

    citation_ready_chunks = [
        item
        for item in retrieved_chunks
        if item.get("distance") is not None
        and item["distance"] <= max_distance
        and _has_valid_line_span(item.get("metadata", {}))
    ]

    if len(citation_ready_chunks) < min_chunks:
        return False

    unique_spans = {
        (
            item["metadata"]["path"],
            item["metadata"]["start_line"],
            item["metadata"]["end_line"],
        )
        for item in citation_ready_chunks
        if "metadata" in item and _has_valid_line_span(item["metadata"])
    }

    return len(unique_spans) >= min_chunks
