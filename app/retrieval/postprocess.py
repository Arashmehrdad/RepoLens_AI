"""Post-processing helpers for retrieved chunks."""


def clean_retrieved_chunks(retrieved_chunks: list[dict]) -> list[dict]:
    """Filter noise while preserving multiple useful files per answer."""
    cleaned = []
    seen_chunk_ids = set()

    for item in retrieved_chunks:
        metadata = item.get("metadata", {})
        path = metadata.get("path", "").lower()
        chunk_index = metadata.get("chunk_index")
        chunk_id = (path, chunk_index)

        if not path:
            continue

        if path.startswith("tests/") or "/tests/" in path:
            continue

        if chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk_id)
        cleaned.append(item)

    return cleaned
