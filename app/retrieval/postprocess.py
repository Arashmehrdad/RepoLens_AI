"""Post-processing helpers for retrieved chunks."""


def clean_retrieved_chunks(
    retrieved_chunks: list[dict],
    query_intents: set[str] | None = None,
) -> list[dict]:
    """Filter noise while preserving multiple useful files per answer."""
    cleaned = []
    seen_chunk_ids = set()
    chunks_per_path = {}
    intents = query_intents or set()
    allow_test_files = bool({"debug", "testing"} & intents)
    allow_extra_spans = bool({"setup", "release", "deployment", "debug", "testing"} & intents)

    for item in retrieved_chunks:
        metadata = item.get("metadata", {})
        path = metadata.get("path", "").lower()
        chunk_index = metadata.get("chunk_index")
        chunk_id = (path, chunk_index)

        if not path:
            continue

        if not allow_test_files and (path.startswith("tests/") or "/tests/" in path):
            continue

        if chunk_id in seen_chunk_ids:
            continue

        prefer_multiple_spans = any(
            metadata.get(flag)
            for flag in (
                "is_readme",
                "is_changelog",
                "is_release_note",
                "is_deployment_file",
                "is_architecture_doc",
            )
        )
        per_file_limit = (
            3
            if prefer_multiple_spans and allow_extra_spans
            else 2
            if prefer_multiple_spans or allow_extra_spans
            else 1
        )
        if chunks_per_path.get(path, 0) >= per_file_limit:
            continue

        seen_chunk_ids.add(chunk_id)
        chunks_per_path[path] = chunks_per_path.get(path, 0) + 1
        cleaned.append(item)

    return cleaned
