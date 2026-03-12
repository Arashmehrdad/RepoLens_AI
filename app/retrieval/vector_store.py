"""Chroma vector collection helpers."""

import chromadb

from app.core.config import VECTOR_STORE_DIR


def get_vector_collection(name: str = "repo_chunks"):
    """Return a persistent Chroma collection by name."""
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    collection = client.get_or_create_collection(name=name)

    return collection
