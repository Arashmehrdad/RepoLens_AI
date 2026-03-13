"""Chroma vector collection helpers."""

import chromadb
from chromadb.api.types import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.core.config import EMBEDDING_CACHE_DIR, VECTOR_STORE_DIR
from app.core.errors import VectorStoreError


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


def reset_vector_collection(name: str) -> None:
    """Delete a persistent collection so re-ingestion does not keep stale chunks."""
    try:
        client = get_vector_client()
        try:
            client.delete_collection(name)
        except Exception as exc:  # pylint: disable=broad-except
            if "not found" not in str(exc).lower():
                raise
    except VectorStoreError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise VectorStoreError(
            "The vector store collection could not be reset.",
            error_code="vector_store_reset_failed",
            diagnostics={"collection_name": name, "reason": str(exc)},
        ) from exc
