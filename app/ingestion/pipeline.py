"""Repository ingestion pipeline helpers."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

from app.core.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from app.core.errors import IngestionLimitError
from app.ingestion.document_loader import load_documents_with_stats
from app.ingestion.file_loader import discover_files
from app.ingestion.repo_manager import clone_repo
from app.retrieval.chunker import chunk_documents
from app.retrieval.indexer import index_chunks


def normalize_repo_url(repo_url: str) -> str:
    """Normalize a repository URL for deterministic collection naming."""
    cleaned_url = repo_url.strip()
    if not cleaned_url:
        raise ValueError("Repository URL must not be empty.")

    candidate_path = Path(cleaned_url)
    if "://" not in cleaned_url and candidate_path.exists():
        return candidate_path.resolve().as_posix()

    if "://" not in cleaned_url:
        return cleaned_url.rstrip("/").removesuffix(".git")

    parsed_url = urlsplit(cleaned_url)
    if parsed_url.scheme.lower() == "file":
        local_path = _file_url_to_path(cleaned_url)
        return local_path.resolve().as_posix()

    normalized_path = parsed_url.path.rstrip("/").removesuffix(".git")
    return urlunsplit(
        (
            parsed_url.scheme.lower(),
            parsed_url.netloc.lower(),
            normalized_path,
            "",
            "",
        )
    )


def build_collection_name(repo_url: str) -> str:
    """Build a deterministic vector collection name from a repository URL."""
    normalized_repo_url = normalize_repo_url(repo_url)
    repo_name = normalized_repo_url.split("/")[-1]
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name.lower())
    return f"repo_{safe_name}"


def resolve_collection_name(
    repo_url: str | None = None,
    collection_name: str | None = None,
) -> str:
    """Resolve the collection name used for repository question answering."""
    if repo_url and repo_url.strip():
        return build_collection_name(repo_url)

    if collection_name and collection_name.strip():
        return collection_name.strip()

    raise ValueError("Either repo_url or collection_name must be provided.")


def _file_url_to_path(repo_url: str) -> Path:
    """Convert a local file URL into a filesystem path."""
    parsed_url = urlsplit(repo_url)
    raw_path = unquote(parsed_url.path)
    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    return Path(raw_path)


def _resolve_repo_path(repo_url: str) -> Path:
    """Resolve a repository URL to either a local path or a cloned checkout."""
    cleaned_url = repo_url.strip()
    local_path = Path(cleaned_url)
    if local_path.exists():
        return local_path.resolve()

    if cleaned_url.startswith("file://"):
        return _file_url_to_path(cleaned_url).resolve()

    return clone_repo(repo_url)


def ingest_repository(repo_url: str) -> dict:
    """Clone a repository, ingest supported files, and index the resulting chunks."""
    repo_path = _resolve_repo_path(repo_url)
    discovery = discover_files(repo_path)
    file_paths = discovery["files"]
    document_result = load_documents_with_stats(file_paths, repo_path)
    documents = document_result["documents"]

    if not documents:
        raise IngestionLimitError(
            "No supported repository files were available within the configured ingestion limits.",
            error_code="ingestion_no_supported_files",
            diagnostics={
                "repo_url": normalize_repo_url(repo_url),
                "discovery": discovery,
                "loading": document_result,
            },
        )

    chunks = chunk_documents(
        documents,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )

    collection_name = build_collection_name(repo_url)
    indexed_count = index_chunks(chunks, collection_name=collection_name)

    return {
        "repo_path": str(repo_path),
        "collection_name": collection_name,
        "file_count": len(file_paths),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "indexed_count": indexed_count,
        "ingestion_diagnostics": {
            "discovery": {
                "selected_files": len(file_paths),
                "total_bytes": discovery["total_bytes"],
                "skipped_reasons": discovery["skipped_reasons"],
            },
            "loading": {
                "loaded_documents": len(documents),
                "skipped_reasons": document_result["skipped_reasons"],
            },
            "chunking": {
                "chunk_size": DEFAULT_CHUNK_SIZE,
                "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
            },
        },
    }
