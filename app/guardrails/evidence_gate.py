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


def _passes_similarity_threshold(
    item: dict,
    max_distance: float,
    min_rerank_score: float,
) -> bool:
    """Return True when a chunk is close enough or strongly reranked."""
    distance = item.get("distance")
    rerank_score = item.get("rerank_score", 0.0)

    if distance is not None and distance <= max_distance:
        return True

    return rerank_score >= min_rerank_score


def has_enough_evidence(
    retrieved_chunks: list[dict],
    min_chunks: int = 1,
    max_distance: float = 1.5,
    min_rerank_score: float = 4.0,
) -> bool:
    """Return True when retrieval results meet minimum evidence thresholds."""
    if len(retrieved_chunks) < min_chunks:
        return False

    citation_ready_chunks = [
        item
        for item in retrieved_chunks
        if _passes_similarity_threshold(
            item,
            max_distance=max_distance,
            min_rerank_score=min_rerank_score,
        )
        and _has_valid_line_span(item.get("metadata", {}))
    ]

    if len(citation_ready_chunks) < min_chunks:
        return False

    matched_intents = {
        intent
        for item in retrieved_chunks
        for intent in item.get("matched_intents", [])
    }
    if "training" in matched_intents and not any(
        item.get("metadata", {}).get("is_training")
        for item in citation_ready_chunks
    ):
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
