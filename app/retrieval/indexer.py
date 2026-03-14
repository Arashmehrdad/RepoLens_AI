"""Vector indexing helpers."""

from app.retrieval.vector_store import (
    delete_chunk_ids,
    get_vector_collection,
    reset_vector_collection,
)


def build_chunk_id(path: str, chunk_index: int) -> str:
    """Build the stable vector-store ID for one chunk."""
    return f"{path}::chunk_{chunk_index}"


def _build_upsert_payload(chunks: list[dict]) -> dict:
    """Convert chunk records into Chroma upsert payloads."""
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(build_chunk_id(chunk["path"], chunk["chunk_index"]))
        documents.append(chunk["content"])
        metadatas.append(
            {
                "path": chunk["path"],
                "path_lower": chunk["path_lower"],
                "filename": chunk["filename"],
                "filename_lower": chunk["filename_lower"],
                "suffix": chunk["suffix"],
                "stem": chunk["stem"],
                "parent_dirs_joined": chunk["parent_dirs_joined"],
                "depth": chunk["depth"],
                "chunk_index": chunk["chunk_index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "section": chunk["section"],
                "symbol": chunk["symbol"],
                "is_readme": chunk["is_readme"],
                "is_config": chunk["is_config"],
                "is_docker": chunk["is_docker"],
                "is_compose": chunk["is_compose"],
                "is_api": chunk["is_api"],
                "is_app_entry": chunk["is_app_entry"],
                "is_training": chunk["is_training"],
                "is_workflow": chunk["is_workflow"],
                "is_dependency_file": chunk["is_dependency_file"],
                "is_changelog": chunk["is_changelog"],
                "is_release_note": chunk["is_release_note"],
                "is_version_file": chunk["is_version_file"],
                "is_deployment_file": chunk["is_deployment_file"],
                "is_docs_update": chunk["is_docs_update"],
                "is_architecture_doc": chunk["is_architecture_doc"],
                "is_test_file": chunk["is_test_file"],
                "is_example_file": chunk.get("is_example_file", False),
                "is_ci_file": chunk.get("is_ci_file", False),
                "is_package_config": chunk.get("is_package_config", False),
                "is_tutorial_doc": chunk.get("is_tutorial_doc", False),
            }
        )

    return {
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas,
    }


def upsert_chunks(chunks: list[dict], collection_name: str = "repo_chunks") -> int:
    """Upsert chunk content plus rich metadata into the vector store."""
    payload = _build_upsert_payload(chunks)
    if not payload["ids"]:
        return 0

    collection = get_vector_collection(collection_name)
    collection.upsert(
        ids=payload["ids"],
        documents=payload["documents"],
        metadatas=payload["metadatas"],
    )
    return len(payload["ids"])


def replace_chunks(chunks: list[dict], collection_name: str = "repo_chunks") -> int:
    """Replace a collection with a new full set of chunk records."""
    reset_vector_collection(collection_name)
    return upsert_chunks(chunks, collection_name=collection_name)


def index_chunks(chunks: list[dict], collection_name: str = "repo_chunks") -> int:
    """Replace the collection with a fresh chunk set for compatibility callers."""
    return replace_chunks(chunks, collection_name=collection_name)


def remove_chunks(chunk_ids: list[str], collection_name: str = "repo_chunks") -> int:
    """Delete chunk IDs from a collection and return the count removed."""
    if not chunk_ids:
        return 0

    delete_chunk_ids(collection_name, chunk_ids)
    return len(chunk_ids)


def count_chunks_for_manifest(manifest_files: dict) -> int:
    """Return the total chunk count described by manifest file entries."""
    return sum(len(entry.get("chunk_ids", [])) for entry in manifest_files.values())
