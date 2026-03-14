"""Incremental-ingestion manifest helpers."""

from __future__ import annotations

import json
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.core.errors import RepoStateError
from app.ingestion.state import RepoState, build_manifest_path
from app.retrieval.indexer import build_chunk_id


FLAG_FIELDS = (
    "is_readme",
    "is_config",
    "is_docker",
    "is_compose",
    "is_api",
    "is_app_entry",
    "is_training",
    "is_workflow",
    "is_dependency_file",
    "is_changelog",
    "is_release_note",
    "is_version_file",
    "is_deployment_file",
    "is_docs_update",
    "is_architecture_doc",
    "is_test_file",
    "is_example_file",
    "is_ci_file",
    "is_package_config",
    "is_tutorial_doc",
)


def load_ingestion_manifest(state_id: str) -> dict | None:
    """Load the saved manifest for one repo state when it exists."""
    manifest_path = build_manifest_path(state_id)
    if not manifest_path.exists():
        return None

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RepoStateError(
            "The ingestion manifest could not be loaded.",
            error_code="manifest_load_failed",
            diagnostics={"state_id": state_id, "reason": str(exc)},
        ) from exc


def _build_flags(document: dict) -> dict:
    """Return the file-level classification flags stored in the manifest."""
    return {
        field: bool(document.get(field))
        for field in FLAG_FIELDS
    }


def _build_file_entry(document: dict, chunk_ids: list[str]) -> dict:
    """Build one manifest entry for a single repository file."""
    content = document.get("content", "")
    file_hash = document.get("content_hash")
    if not file_hash:
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    size = document.get("byte_size")
    if size is None:
        size = len(content.encode("utf-8"))

    return {
        "path": document["path"],
        "file_hash": file_hash,
        "size": size,
        "chunk_ids": chunk_ids,
        "flags": _build_flags(document),
    }


def build_manifest_files(
    documents: list[dict],
    existing_files: dict | None = None,
    chunks_by_path: dict | None = None,
) -> dict:
    """Build the final manifest file inventory for one repo state."""
    existing_files = existing_files or {}
    chunks_by_path = chunks_by_path or {}
    files = {}

    for document in documents:
        path = document["path"]
        if path in chunks_by_path:
            files[path] = _build_file_entry(document, chunks_by_path[path])
            continue

        existing_entry = existing_files.get(path)
        if existing_entry:
            files[path] = existing_entry
            continue

        files[path] = _build_file_entry(document, [])

    return files


def build_incremental_plan(existing_manifest: dict | None, documents: list[dict]) -> dict:
    """Compare the current repo documents against the saved manifest."""
    existing_files = (existing_manifest or {}).get("files", {})
    current_documents = {document["path"]: document for document in documents}
    current_paths = set(current_documents)
    existing_paths = set(existing_files)

    added_paths = sorted(current_paths - existing_paths)
    removed_paths = sorted(existing_paths - current_paths)
    changed_paths = sorted(
        path
        for path in current_paths & existing_paths
        if current_documents[path]["content_hash"] != existing_files[path]["file_hash"]
    )
    unchanged_paths = sorted(
        path
        for path in current_paths & existing_paths
        if current_documents[path]["content_hash"] == existing_files[path]["file_hash"]
    )

    return {
        "added_paths": added_paths,
        "changed_paths": changed_paths,
        "removed_paths": removed_paths,
        "unchanged_paths": unchanged_paths,
        "changed_documents": [current_documents[path] for path in changed_paths],
        "added_documents": [current_documents[path] for path in added_paths],
        "unchanged_documents": [current_documents[path] for path in unchanged_paths],
        "removed_entries": [existing_files[path] for path in removed_paths],
        "existing_files": existing_files,
    }


def build_chunk_ids_for_path(chunks: list[dict]) -> dict[str, list[str]]:
    """Group produced chunk IDs by relative repository path."""
    grouped = {}

    for chunk in chunks:
        chunk_id = build_chunk_id(chunk["path"], chunk["chunk_index"])
        grouped.setdefault(chunk["path"], []).append(chunk_id)

    return grouped


def save_ingestion_manifest(
    state: RepoState,
    documents: list[dict],
    chunks_by_path: dict,
    existing_files: dict | None = None,
    incremental_stats: dict | None = None,
) -> Path:
    """Persist the final manifest for one repo state."""
    manifest_path = build_manifest_path(state.state_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    files = build_manifest_files(
        documents,
        existing_files=existing_files,
        chunks_by_path=chunks_by_path,
    )
    payload = {
        "state": state.to_dict(),
        "saved_at": datetime.now(UTC).isoformat(),
        "chunk_count": sum(len(entry.get("chunk_ids", [])) for entry in files.values()),
        "files": files,
        "incremental_stats": incremental_stats or {},
    }

    try:
        manifest_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise RepoStateError(
            "The ingestion manifest could not be saved.",
            error_code="manifest_save_failed",
            diagnostics={"state_id": state.state_id, "reason": str(exc)},
        ) from exc

    return manifest_path


def extract_chunk_ids(entries: list[dict]) -> list[str]:
    """Return the flattened chunk IDs stored in manifest file entries."""
    chunk_ids = []

    for entry in entries:
        chunk_ids.extend(entry.get("chunk_ids", []))

    return chunk_ids


def get_manifest_files(manifest: dict | None) -> dict:
    """Return the file inventory from a manifest-like payload."""
    if not manifest:
        return {}

    return manifest.get("files", {})


def load_manifest_for_state(state: RepoState) -> dict | None:
    """Load the manifest for a repo state object."""
    return load_ingestion_manifest(state.state_id)
