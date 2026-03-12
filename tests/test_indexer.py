"""Tests for vector indexing."""

from app.retrieval import indexer


class FakeCollection:
    """Minimal vector collection stub for indexer tests."""

    def __init__(self):
        self.calls = []

    def upsert(self, ids, documents, metadatas):
        """Record upsert calls for assertions."""
        self.calls.append(
            {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
        )


def test_index_chunks_upserts_rich_metadata(monkeypatch):
    """Indexing should write chunk text plus reranking metadata to the store."""
    collection = FakeCollection()
    chunk = {
        "content": "Run the app with uvicorn.",
        "path": "README.md",
        "path_lower": "readme.md",
        "filename": "README.md",
        "filename_lower": "readme.md",
        "suffix": ".md",
        "stem": "readme",
        "parent_dirs_joined": "",
        "depth": 1,
        "chunk_index": 0,
        "is_readme": True,
        "is_config": False,
        "is_docker": False,
        "is_compose": False,
        "is_api": False,
        "is_app_entry": False,
        "is_training": False,
        "is_workflow": False,
        "is_dependency_file": False,
    }

    monkeypatch.setattr(indexer, "get_vector_collection", lambda name: collection)

    indexed_count = indexer.index_chunks([chunk])

    assert indexed_count == 1
    assert collection.calls[0]["ids"] == ["README.md::chunk_0"]
    assert collection.calls[0]["documents"] == ["Run the app with uvicorn."]
    assert collection.calls[0]["metadatas"][0]["is_readme"] is True
