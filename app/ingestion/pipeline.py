"""Repository ingestion pipeline helpers."""

import re
from urllib.parse import urlsplit, urlunsplit

from app.ingestion.repo_manager import clone_repo
from app.ingestion.file_loader import list_supported_files
from app.ingestion.document_loader import load_documents
from app.retrieval.chunker import chunk_documents
from app.retrieval.indexer import index_chunks


def normalize_repo_url(repo_url: str) -> str:
    """Normalize a repository URL for deterministic collection naming."""
    cleaned_url = repo_url.strip()
    if not cleaned_url:
        raise ValueError("Repository URL must not be empty.")

    if "://" not in cleaned_url:
        return cleaned_url.rstrip("/").removesuffix(".git")

    parsed_url = urlsplit(cleaned_url)
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


def ingest_repository(repo_url: str) -> dict:
    """Clone a repository, ingest supported files, and index the resulting chunks."""
    repo_path = clone_repo(repo_url)
    file_paths = list_supported_files(repo_path)
    documents = load_documents(file_paths, repo_path)
    chunks = chunk_documents(documents)

    collection_name = build_collection_name(repo_url)
    indexed_count = index_chunks(chunks, collection_name=collection_name)

    return {
        "repo_path": str(repo_path),
        "collection_name": collection_name,
        "file_count": len(file_paths),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "indexed_count": indexed_count,
    }
