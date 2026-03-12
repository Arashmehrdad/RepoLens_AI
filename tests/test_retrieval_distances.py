"""Tests for retrieval distance handling."""

from app.retrieval import retriever


class FakeCollection:
    """Collection stub that returns fixed retrieval results."""

    def query(self, query_texts, n_results):
        """Return canned documents, metadata, and distances."""
        return {
            "documents": [["config details", "readme details"]],
            "metadatas": [[
                {
                    "path": "config/settings.yaml",
                    "path_lower": "config/settings.yaml",
                    "filename": "settings.yaml",
                    "filename_lower": "settings.yaml",
                    "chunk_index": 0,
                    "start_line": 3,
                    "end_line": 12,
                    "section": "",
                    "symbol": "",
                    "is_readme": False,
                    "is_config": True,
                    "is_dependency_file": False,
                    "is_app_entry": False,
                    "is_api": False,
                    "is_training": False,
                    "is_docker": False,
                    "is_compose": False,
                    "is_workflow": False,
                    "is_changelog": False,
                    "is_release_note": False,
                    "is_version_file": False,
                    "is_deployment_file": False,
                    "is_docs_update": False,
                    "is_architecture_doc": False,
                    "is_test_file": False,
                },
                {
                    "path": "README.md",
                    "path_lower": "readme.md",
                    "filename": "README.md",
                    "filename_lower": "readme.md",
                    "chunk_index": 0,
                    "start_line": 12,
                    "end_line": 28,
                    "section": "Setup",
                    "symbol": "",
                    "is_readme": True,
                    "is_config": False,
                    "is_dependency_file": False,
                    "is_app_entry": False,
                    "is_api": False,
                    "is_training": False,
                    "is_docker": False,
                    "is_compose": False,
                    "is_workflow": False,
                    "is_changelog": False,
                    "is_release_note": False,
                    "is_version_file": False,
                    "is_deployment_file": False,
                    "is_docs_update": True,
                    "is_architecture_doc": False,
                    "is_test_file": False,
                },
            ]],
            "distances": [[0.25, 0.75]],
        }


def test_retrieve_chunks_preserves_distance_values(monkeypatch):
    """Distances from the vector store should remain attached to the right chunk."""
    monkeypatch.setattr(retriever, "get_vector_collection", lambda name: FakeCollection())

    results = retriever.retrieve_chunks("Where is the config?", n_results=2)
    distances_by_path = {item["metadata"]["path"]: item["distance"] for item in results}

    assert distances_by_path["config/settings.yaml"] == 0.25
    assert distances_by_path["README.md"] == 0.75
