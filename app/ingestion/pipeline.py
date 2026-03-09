import re

from app.ingestion.repo_manager import clone_repo
from app.ingestion.file_loader import list_supported_files
from app.ingestion.document_loader import load_documents
from app.retrieval.chunker import chunk_documents
from app.retrieval.indexer import index_chunks


def build_collection_name(repo_url: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name.lower())
    return f"repo_{safe_name}"


def ingest_repository(repo_url: str) -> dict:
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