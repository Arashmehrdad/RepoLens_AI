"""Post-processing helpers for retrieved chunks."""


def _build_postprocess_policy(query_intents: set[str] | None) -> dict:
    """Return filtering rules driven by the matched query intents."""
    intents = query_intents or set()
    return {
        "allow_test_files": bool({"debug", "testing"} & intents),
        "allow_example_files": bool({"setup", "api", "debug", "testing"} & intents),
        "allow_extra_spans": bool(
            {"setup", "release", "deployment", "debug", "testing", "architecture"}
            & intents
        ),
    }


def _build_content_signature(item: dict) -> str:
    """Return a stable content signature for duplicate detection."""
    normalized_content = " ".join(item.get("content", "").split())
    return normalized_content[:240]


def _per_file_limit(metadata: dict, allow_extra_spans: bool) -> int:
    """Return how many chunks from one file should survive cleanup."""
    prefer_multiple_spans = any(
        metadata.get(flag)
        for flag in (
            "is_readme",
            "is_changelog",
            "is_release_note",
            "is_deployment_file",
            "is_architecture_doc",
            "is_tutorial_doc",
        )
    )

    if prefer_multiple_spans and allow_extra_spans:
        return 3
    if prefer_multiple_spans or allow_extra_spans:
        return 2
    return 1


def _is_test_path(path: str) -> bool:
    """Return True when the path points at a test file."""
    return path.startswith("tests/") or "/tests/" in path


def _should_drop_chunk(item: dict, policy: dict, state: dict) -> bool:
    """Return True when a retrieved chunk should be filtered out."""
    metadata = item.get("metadata", {})
    path = metadata.get("path", "").lower()
    chunk_id = (path, metadata.get("chunk_index"))
    content_signature = _build_content_signature(item)
    drop_reason = None

    if not path:
        drop_reason = None
    elif not policy["allow_test_files"] and _is_test_path(path):
        drop_reason = "dropped_test_files"
    elif metadata.get("is_example_file") and not policy["allow_example_files"]:
        drop_reason = "dropped_example_files"
    elif chunk_id in state["seen_chunk_ids"]:
        drop_reason = "dropped_duplicate_chunks"
    elif content_signature and content_signature in state["seen_signatures"]:
        drop_reason = "dropped_duplicate_content"
    elif state["chunks_per_path"].get(path, 0) >= _per_file_limit(
        metadata,
        allow_extra_spans=policy["allow_extra_spans"],
    ):
        drop_reason = "dropped_per_file_limit"

    if drop_reason:
        state["diagnostics"][drop_reason] += 1
        return True

    if not path:
        return True

    state["seen_chunk_ids"].add(chunk_id)
    if content_signature:
        state["seen_signatures"].add(content_signature)
    state["chunks_per_path"][path] = state["chunks_per_path"].get(path, 0) + 1
    return False


def clean_retrieved_chunks(
    retrieved_chunks: list[dict],
    query_intents: set[str] | None = None,
    return_diagnostics: bool = False,
) -> list[dict] | tuple[list[dict], dict]:
    """Filter noise while preserving multiple useful files per answer."""
    cleaned = []
    policy = _build_postprocess_policy(query_intents)
    state = {
        "seen_chunk_ids": set(),
        "seen_signatures": set(),
        "chunks_per_path": {},
        "diagnostics": {
            "input_count": len(retrieved_chunks),
            "dropped_test_files": 0,
            "dropped_example_files": 0,
            "dropped_duplicate_chunks": 0,
            "dropped_duplicate_content": 0,
            "dropped_per_file_limit": 0,
        },
    }

    for item in retrieved_chunks:
        if _should_drop_chunk(item, policy, state):
            continue

        cleaned.append(item)

    state["diagnostics"]["output_count"] = len(cleaned)

    if not return_diagnostics:
        return cleaned

    return cleaned, state["diagnostics"]
