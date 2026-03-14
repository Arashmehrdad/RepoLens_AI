"""Repository ingestion pipeline helpers."""

from pathlib import Path

from app.core.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from app.core.errors import IngestionLimitError, RepoStateError
from app.ingestion.document_loader import load_documents_with_stats
from app.ingestion.file_loader import discover_files
from app.ingestion.manifest import (
    build_chunk_ids_for_path,
    build_incremental_plan,
    extract_chunk_ids,
    get_manifest_files,
    load_manifest_for_state,
    save_ingestion_manifest,
)
from app.ingestion.repo_manager import clone_repo, get_repo_commit_sha
from app.ingestion.state import (
    RepoState,
    build_collection_name as build_state_collection_name,
    build_repo_state,
    file_url_to_path,
    normalize_ref,
    normalize_repo_url as normalize_state_repo_url,
    resolve_collection_name as resolve_state_collection_name,
)
from app.retrieval.chunker import chunk_documents
from app.retrieval.indexer import (
    count_chunks_for_manifest,
    index_chunks,
    remove_chunks,
    upsert_chunks,
)
from app.retrieval.vector_store import vector_collection_exists


def normalize_repo_url(repo_url: str) -> str:
    """Normalize a repository URL for deterministic collection naming."""
    return normalize_state_repo_url(repo_url)


def build_collection_name(repo_url: str, ref: str | None = None) -> str:
    """Build a deterministic vector collection name from a repository URL."""
    return build_state_collection_name(repo_url, ref=ref)


def resolve_collection_name(
    repo_url: str | None = None,
    collection_name: str | None = None,
    ref: str | None = None,
) -> str:
    """Resolve the collection name used for repository question answering."""
    return resolve_state_collection_name(
        repo_url=repo_url,
        collection_name=collection_name,
        ref=ref,
    )


def _ensure_existing_repo_path(repo_path: Path, repo_url: str) -> Path:
    """Validate a resolved local repo path before ingestion continues."""
    if repo_path.exists() and repo_path.is_dir():
        return repo_path.resolve()

    raise RepoStateError(
        "The requested local repository path does not exist.",
        error_code="repo_state_missing_path",
        diagnostics={"repo_url": repo_url, "repo_path": str(repo_path)},
    )


def _resolve_repo_path(repo_url: str, ref: str | None, state_id: str) -> Path:
    """Resolve a repository URL to either a local path or a cloned checkout."""
    cleaned_url = repo_url.strip()
    normalized_ref = normalize_ref(ref)

    if normalized_ref != "default":
        return clone_repo(
            repo_url,
            ref=normalized_ref,
            target_dir_name=state_id,
        )

    local_path = Path(cleaned_url)
    if local_path.exists():
        return _ensure_existing_repo_path(local_path, repo_url)

    if cleaned_url.startswith("file://"):
        return _ensure_existing_repo_path(file_url_to_path(cleaned_url), repo_url)

    return clone_repo(repo_url)


def _build_discovery_diagnostics(discovery: dict) -> dict:
    """Return the stable discovery summary exposed in ingestion diagnostics."""
    return {
        "selected_files": len(discovery["files"]),
        "total_bytes": discovery["total_bytes"],
        "skipped_reasons": discovery["skipped_reasons"],
    }


def _build_loading_diagnostics(document_result: dict) -> dict:
    """Return the stable loading summary exposed in ingestion diagnostics."""
    return {
        "loaded_documents": len(document_result["documents"]),
        "skipped_reasons": document_result["skipped_reasons"],
    }


def _build_incremental_stats(
    discovery: dict,
    plan: dict,
    chunks_added: int,
    chunks_removed: int,
    incremental_used: bool,
) -> dict:
    """Build incremental-ingestion counters for API/UI diagnostics."""
    files_scanned = len(discovery["files"])
    files_added = len(plan["added_paths"])
    files_changed = len(plan["changed_paths"])
    files_removed = len(plan["removed_paths"])
    files_unchanged = len(plan["unchanged_paths"])
    cache_hit_rate = (
        round(files_unchanged / files_scanned, 3)
        if files_scanned
        else 0.0
    )
    return {
        "files_scanned": files_scanned,
        "files_added": files_added,
        "files_changed": files_changed,
        "files_removed": files_removed,
        "files_unchanged": files_unchanged,
        "chunks_added": chunks_added,
        "chunks_removed": chunks_removed,
        "incremental_used": incremental_used,
        "cache_hit_rate": cache_hit_rate,
    }


def _build_chunking_diagnostics() -> dict:
    """Return the chunking configuration used for this ingestion run."""
    return {
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
    }


def _full_reindex(
    state: RepoState,
    documents: list[dict],
    discovery: dict,
    document_result: dict,
) -> dict:
    """Replace the collection with a fresh chunk set and save the manifest."""
    chunks = chunk_documents(
        documents,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )
    indexed_count = index_chunks(chunks, collection_name=state.collection_name)
    chunks_by_path = build_chunk_ids_for_path(chunks)
    incremental_stats = _build_incremental_stats(
        discovery=discovery,
        plan={
            "added_paths": [document["path"] for document in documents],
            "changed_paths": [],
            "removed_paths": [],
            "unchanged_paths": [],
        },
        chunks_added=indexed_count,
        chunks_removed=0,
        incremental_used=False,
    )
    manifest_path = save_ingestion_manifest(
        state=state,
        documents=documents,
        chunks_by_path=chunks_by_path,
        incremental_stats=incremental_stats,
    )
    return {
        "chunk_count": len(chunks),
        "indexed_count": indexed_count,
        "manifest_path": manifest_path,
        "incremental_stats": incremental_stats,
        "ingestion_diagnostics": {
            "discovery": _build_discovery_diagnostics(discovery),
            "loading": _build_loading_diagnostics(document_result),
            "chunking": _build_chunking_diagnostics(),
            "incremental": incremental_stats,
        },
    }


def _incremental_reindex(
    state: RepoState,
    documents: list[dict],
    discovery: dict,
    document_result: dict,
    existing_manifest: dict,
) -> dict:
    """Update only changed files for a repo state and preserve unchanged chunks."""
    plan = build_incremental_plan(existing_manifest, documents)
    files_to_reindex = plan["added_documents"] + plan["changed_documents"]
    new_chunks = chunk_documents(
        files_to_reindex,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )
    removed_chunk_ids = extract_chunk_ids(plan["removed_entries"])
    removed_chunk_ids.extend(
        extract_chunk_ids(
            [plan["existing_files"][path] for path in plan["changed_paths"]]
        )
    )

    chunks_removed = remove_chunks(
        removed_chunk_ids,
        collection_name=state.collection_name,
    )
    chunks_added = upsert_chunks(new_chunks, collection_name=state.collection_name)
    incremental_stats = _build_incremental_stats(
        discovery=discovery,
        plan=plan,
        chunks_added=chunks_added,
        chunks_removed=chunks_removed,
        incremental_used=True,
    )
    manifest_path = save_ingestion_manifest(
        state=state,
        documents=documents,
        chunks_by_path=build_chunk_ids_for_path(new_chunks),
        existing_files=plan["existing_files"],
        incremental_stats=incremental_stats,
    )
    final_files = get_manifest_files(load_manifest_for_state(state) or {})
    return {
        "chunk_count": count_chunks_for_manifest(final_files),
        "indexed_count": count_chunks_for_manifest(final_files),
        "manifest_path": manifest_path,
        "incremental_stats": incremental_stats,
        "ingestion_diagnostics": {
            "discovery": _build_discovery_diagnostics(discovery),
            "loading": _build_loading_diagnostics(document_result),
            "chunking": _build_chunking_diagnostics(),
            "incremental": incremental_stats,
        },
    }


def ingest_repository_state(
    repo_url: str,
    ref: str | None = None,
) -> dict:
    """Ingest one repository state, using incremental updates when possible."""
    provisional_state = build_repo_state(repo_url, ref=ref)
    repo_path = _resolve_repo_path(repo_url, ref, provisional_state.state_id)
    state = build_repo_state(
        repo_url,
        ref=ref,
        repo_path=repo_path,
        commit_sha=get_repo_commit_sha(repo_path),
    )
    discovery = discover_files(repo_path)
    document_result = load_documents_with_stats(discovery["files"], repo_path)
    documents = document_result["documents"]

    if not documents:
        raise IngestionLimitError(
            "No supported repository files were available within the configured ingestion limits.",
            error_code="ingestion_no_supported_files",
            diagnostics={
                "repo_url": normalize_repo_url(repo_url),
                "ref": state.ref,
                "state_id": state.state_id,
                "discovery": discovery,
                "loading": document_result,
            },
        )

    existing_manifest = load_manifest_for_state(state)
    if existing_manifest and vector_collection_exists(state.collection_name):
        indexing_result = _incremental_reindex(
            state=state,
            documents=documents,
            discovery=discovery,
            document_result=document_result,
            existing_manifest=existing_manifest,
        )
    else:
        indexing_result = _full_reindex(
            state=state,
            documents=documents,
            discovery=discovery,
            document_result=document_result,
        )

    final_manifest = load_manifest_for_state(state) or {}
    final_files = get_manifest_files(final_manifest)
    return {
        "repo_path": str(repo_path),
        "collection_name": state.collection_name,
        "file_count": len(discovery["files"]),
        "document_count": len(documents),
        "chunk_count": count_chunks_for_manifest(final_files),
        "indexed_count": count_chunks_for_manifest(final_files),
        "ingestion_diagnostics": indexing_result["ingestion_diagnostics"],
        "state": state.to_dict(),
        "manifest_path": str(indexing_result["manifest_path"]),
        "incremental_stats": indexing_result["incremental_stats"],
    }


def ingest_repository(repo_url: str) -> dict:
    """Clone a repository, ingest supported files, and index the resulting chunks."""
    return ingest_repository_state(repo_url, ref=None)
