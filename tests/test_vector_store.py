"""Tests for Chroma vector store configuration."""

from pathlib import Path

from app.retrieval import vector_store


class FakeEmbeddingFunction:
    """Simple embedding stub used to inspect configured cache paths."""

    def __init__(self):
        self.DOWNLOAD_PATH = FakeOnnxEmbeddingFunction.DOWNLOAD_PATH


class FakeOnnxEmbeddingFunction:
    """Simple ONNX stub used to inspect the configured download path."""

    DOWNLOAD_PATH = ""


class FakeClient:
    """Minimal PersistentClient stand-in for collection creation tests."""

    def __init__(self, path: str):
        self.path = path
        self.calls = []

    def get_or_create_collection(self, **kwargs):
        """Record collection creation arguments and return them."""
        self.calls.append(kwargs)
        return kwargs

    def delete_collection(self, name: str):
        """Record collection deletion requests for assertions."""
        self.calls.append({"delete_collection": name})


def test_get_embedding_function_uses_repo_local_cache(monkeypatch, tmp_path):
    """Embedding downloads should be redirected into the configured repo cache."""
    monkeypatch.setattr(vector_store, "EMBEDDING_CACHE_DIR", tmp_path / "model-cache")
    monkeypatch.setattr(vector_store, "ONNXMiniLM_L6_V2", FakeOnnxEmbeddingFunction)
    monkeypatch.setattr(vector_store, "DefaultEmbeddingFunction", FakeEmbeddingFunction)

    embedding_function = vector_store._get_embedding_function()

    assert embedding_function.DOWNLOAD_PATH == str(
        Path(tmp_path / "model-cache" / "all-MiniLM-L6-v2")
    )


def test_get_vector_collection_uses_configured_client_and_embedding_function(
    monkeypatch,
    tmp_path,
):
    """Collection setup should stay inside the configured vector store directory."""
    captured = {}

    def build_client(path: str):
        captured["path"] = path
        return FakeClient(path=path)

    monkeypatch.setattr(vector_store, "VECTOR_STORE_DIR", tmp_path / "vector-store")
    monkeypatch.setattr(vector_store, "EMBEDDING_CACHE_DIR", tmp_path / "model-cache")
    monkeypatch.setattr(vector_store, "ONNXMiniLM_L6_V2", FakeOnnxEmbeddingFunction)
    monkeypatch.setattr(vector_store, "DefaultEmbeddingFunction", FakeEmbeddingFunction)
    monkeypatch.setattr(vector_store.chromadb, "PersistentClient", build_client)

    collection = vector_store.get_vector_collection("demo")

    assert captured["path"] == str(Path(tmp_path / "vector-store"))
    assert collection["name"] == "demo"
    assert collection["embedding_function"].DOWNLOAD_PATH == str(
        Path(tmp_path / "model-cache" / "all-MiniLM-L6-v2")
    )


def test_reset_vector_collection_uses_configured_client(monkeypatch, tmp_path):
    """Resetting a collection should delete it through the configured client."""
    captured = {}

    def build_client(path: str):
        client = FakeClient(path=path)
        captured["client"] = client
        return client

    monkeypatch.setattr(vector_store, "VECTOR_STORE_DIR", tmp_path / "vector-store")
    monkeypatch.setattr(vector_store.chromadb, "PersistentClient", build_client)

    vector_store.reset_vector_collection("demo")

    assert captured["client"].calls == [{"delete_collection": "demo"}]
