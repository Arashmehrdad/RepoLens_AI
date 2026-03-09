def has_enough_evidence(
    retrieved_chunks: list[dict],
    min_chunks: int = 1,
    max_distance: float = 1.5,
) -> bool:
    if len(retrieved_chunks) < min_chunks:
        return False

    strong_chunks = [
        item
        for item in retrieved_chunks
        if item.get("distance") is not None and item["distance"] <= max_distance
    ]

    if len(strong_chunks) < min_chunks:
        return False

    unique_paths = {
        item["metadata"]["path"]
        for item in strong_chunks
        if "metadata" in item and "path" in item["metadata"]
    }

    return len(unique_paths) >= 1