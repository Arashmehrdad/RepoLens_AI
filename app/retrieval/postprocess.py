def clean_retrieved_chunks(retrieved_chunks: list[dict]) -> list[dict]:
    cleaned = []
    seen_paths = set()

    for item in retrieved_chunks:
        metadata = item.get("metadata", {})
        path = metadata.get("path", "").lower()

        if not path:
            continue

        if path.startswith("tests/"):
            continue

        if "/tests/" in path:
            continue

        if path in seen_paths:
            continue

        seen_paths.add(path)
        cleaned.append(item)

    return cleaned