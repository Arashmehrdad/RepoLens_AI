"""Chroma vector collection helpers."""

import chromadb
from chromadb.api.types import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.core.config import EMBEDDING_CACHE_DIR, VECTOR_STORE_DIR
from app.core.errors import VectorStoreError


def _is_missing_collection_error(exc: Exception) -> bool:
    """Return True when a collection-reset error only means the collection is absent."""
    message = str(exc).lower()
    return (
        exc.__class__.__name__ == "NotFoundError"
        or "not found" in message
        or "does not exist" in message
    )


def _get_embedding_function() -> DefaultEmbeddingFunction:
    """Return Chroma's default embedding function with a repo-local ONNX cache."""
    try:
        EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = str(EMBEDDING_CACHE_DIR / "all-MiniLM-L6-v2")
        return DefaultEmbeddingFunction()
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store embedding configuration could not be prepared.",
            error_code="vector_store_embedding_error",
            diagnostics={"reason": str(exc)},
        ) from exc


def get_vector_client():
    """Return the persistent Chroma client used by RepoLens collections."""
    try:
        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store is unavailable.",
            error_code="vector_store_unavailable",
            diagnostics={"reason": str(exc)},
        ) from exc


def get_vector_collection(name: str = "repo_chunks"):
    """Return a persistent Chroma collection by name."""
    try:
        client = get_vector_client()
        return client.get_or_create_collection(
            name=name,
            embedding_function=_get_embedding_function(),
        )
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store is unavailable.",
            error_code="vector_store_unavailable",
            diagnostics={"collection_name": name, "reason": str(exc)},
        ) from exc


def vector_collection_exists(name: str) -> bool:
    """Return True when a persistent Chroma collection already exists."""
    try:
        client = get_vector_client()
        collections = client.list_collections()
        return any(
            getattr(collection, "name", collection) == name
            for collection in collections
        )
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store collection list could not be loaded.",
            error_code="vector_store_list_failed",
            diagnostics={"collection_name": name, "reason": str(exc)},
        ) from exc


def delete_chunk_ids(collection_name: str, chunk_ids: list[str]) -> None:
    """Delete chunk IDs from an existing collection when they are present."""
    if not chunk_ids:
        return

    try:
        collection = get_vector_collection(collection_name)
        collection.delete(ids=chunk_ids)
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store chunks could not be deleted.",
            error_code="vector_store_delete_failed",
            diagnostics={
                "collection_name": collection_name,
                "chunk_count": len(chunk_ids),
                "reason": str(exc),
            },
        ) from exc


def get_chunks_by_ids(collection_name: str, chunk_ids: list[str]) -> list[dict]:
    """Return chunk documents and metadata for specific IDs."""
    if not chunk_ids:
        return []

    try:
        collection = get_vector_collection(collection_name)
        results = collection.get(ids=chunk_ids)
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The requested vector-store chunks could not be loaded.",
            error_code="vector_store_get_failed",
            diagnostics={
                "collection_name": collection_name,
                "chunk_count": len(chunk_ids),
                "reason": str(exc),
            },
        ) from exc

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    ids = results.get("ids", [])
    chunks = []

    for index, chunk_id in enumerate(ids):
        chunks.append(
            {
                "id": chunk_id,
                "content": documents[index],
                "metadata": metadatas[index],
            }
        )

    return chunks


def reset_vector_collection(name: str) -> None:
    """Delete a persistent collection so re-ingestion does not keep stale chunks."""
    try:
        client = get_vector_client()
        try:
            client.delete_collection(name)
        except Exception as exc:  # pylint: disable=broad-except
            if not _is_missing_collection_error(exc):
                raise
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store collection could not be reset.",
            error_code="vector_store_reset_failed",
            diagnostics={"collection_name": name, "reason": str(exc)},
        ) from exc
