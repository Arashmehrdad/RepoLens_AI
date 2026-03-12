"""Chroma vector collection helpers."""

import chromadb
from chromadb.api.types import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.core.config import EMBEDDING_CACHE_DIR, VECTOR_STORE_DIR


def _get_embedding_function() -> DefaultEmbeddingFunction:
    """Return Chroma's default embedding function with a repo-local ONNX cache."""
    EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = str(EMBEDDING_CACHE_DIR / "all-MiniLM-L6-v2")
    return DefaultEmbeddingFunction()


def get_vector_collection(name: str = "repo_chunks"):
    """Return a persistent Chroma collection by name."""
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    return client.get_or_create_collection(
        name=name,
        embedding_function=_get_embedding_function(),
    )
