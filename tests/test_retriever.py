"""Tests for retrieval reranking behavior."""

from app.retrieval import retriever


class FakeCollection:
    """Collection stub that records query calls and returns canned results."""

    def __init__(self):
        self.calls = []

    def query(self, query_texts, n_results):
        """Return fixed retrieval results for reranking assertions."""
        self.calls.append({"query_texts": query_texts, "n_results": n_results})
        return {
            "documents": [["utility details", "run instructions"]],
            "metadatas": [[
                {
                    "path": "app/utils/helpers.py",
                    "path_lower": "app/utils/helpers.py",
                    "filename": "helpers.py",
                    "filename_lower": "helpers.py",
                    "chunk_index": 1,
                    "start_line": 40,
                    "end_line": 55,
                    "section": "",
                    "symbol": "format_text",
                    "is_readme": False,
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
                    "is_docs_update": False,
                    "is_architecture_doc": False,
                    "is_test_file": False,
                    "is_example_file": False,
                    "is_ci_file": False,
                    "is_package_config": False,
                    "is_tutorial_doc": False,
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
                    "is_example_file": False,
                    "is_ci_file": False,
                    "is_package_config": False,
                    "is_tutorial_doc": True,
                },
            ]],
            "distances": [[0.1, 0.6]],
        }


def test_retrieve_chunks_fetches_extra_candidates_and_reranks(monkeypatch):
    """Retriever should fetch extra candidates, rerank them, and truncate the result list."""
    collection = FakeCollection()
    monkeypatch.setattr(retriever, "get_vector_collection", lambda name: collection)

    results = retriever.retrieve_chunks("How do I run this project?", n_results=2)

    assert collection.calls == [{"query_texts": ["How do I run this project?"], "n_results": 18}]
    assert len(results) == 2
    assert results[0]["metadata"]["path"] == "README.md"
    assert results[0]["matched_intents"] == ["setup"]


def test_retrieve_chunks_can_return_diagnostics(monkeypatch):
    """Retriever diagnostics should include intents and ranking previews."""
    collection = FakeCollection()
    monkeypatch.setattr(retriever, "get_vector_collection", lambda name: collection)

    results, diagnostics = retriever.retrieve_chunks(
        "How do I run this project?",
        n_results=2,
        return_diagnostics=True,
    )

    assert len(results) == 2
    assert diagnostics["matched_intents"] == ["setup"]
    assert diagnostics["query_versions"] == []
    assert diagnostics["fetch_count"] == 18
    assert diagnostics["raw_result_count"] == 2
    assert diagnostics["top_candidates"][0]["path"] == "README.md"
    assert "is_readme" in diagnostics["top_candidates"][0]["flags"]


def test_retrieve_chunks_wraps_collection_failures(monkeypatch):
    """Collection failures should become structured retrieval errors."""

    def fail_collection(name):
        raise retriever.VectorStoreError(
            "vector store unavailable",
            error_code="vector_store_unavailable",
        )

    monkeypatch.setattr(retriever, "get_vector_collection", fail_collection)

    try:
        retriever.retrieve_chunks("How do I run this project?", n_results=2)
    except retriever.RetrievalError as exc:
        assert exc.error_code == "vector_store_unavailable"
    else:
        raise AssertionError("Expected RetrievalError to be raised")


def test_retrieve_chunks_prefers_release_content_with_matching_version(monkeypatch):
    """Release-mode reranking should boost chunks that mention the requested version."""

    class ReleaseCollection:
        """Collection stub for version-aware release ranking tests."""

        def query(self, query_texts, n_results):
            del query_texts, n_results
            return {
                "documents": [[
                    "General project overview without a concrete version token.",
                    "v0.5.0 adds versioned eval reports and safer fallback answers.",
                ]],
                "metadatas": [[
                    {
                        "path": "README.md",
                        "path_lower": "readme.md",
                        "filename": "README.md",
                        "filename_lower": "readme.md",
                        "chunk_index": 0,
                        "start_line": 1,
                        "end_line": 18,
                        "section": "Overview",
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
                        "is_example_file": False,
                        "is_ci_file": False,
                        "is_package_config": False,
                        "is_tutorial_doc": False,
                    },
                    {
                        "path": "README.md",
                        "path_lower": "readme.md",
                        "filename": "README.md",
                        "filename_lower": "readme.md",
                        "chunk_index": 1,
                        "start_line": 120,
                        "end_line": 145,
                        "section": "v0.5.0 Release Summary",
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
                        "is_example_file": False,
                        "is_ci_file": False,
                        "is_package_config": False,
                        "is_tutorial_doc": False,
                    },
                ]],
                "distances": [[0.1, 0.5]],
            }

    monkeypatch.setattr(
        retriever,
        "get_vector_collection",
        lambda name: ReleaseCollection(),
    )

    results, diagnostics = retriever.retrieve_chunks(
        "What changed in v0.5.0?",
        n_results=2,
        mode="release",
        return_diagnostics=True,
    )

    assert results[0]["metadata"]["chunk_index"] == 1
    assert diagnostics["query_versions"] == ["v0.5.0"]


def test_retrieve_chunks_uses_wider_fetch_window_for_release_mode(monkeypatch):
    """Release-style queries should fetch a larger candidate pool before reranking."""
    collection = FakeCollection()
    monkeypatch.setattr(retriever, "get_vector_collection", lambda name: collection)

    retriever.retrieve_chunks(
        "What deployment artifacts are available for this project?",
        n_results=2,
        mode="release",
    )

    assert collection.calls == [
        {
            "query_texts": ["What deployment artifacts are available for this project?"],
            "n_results": 60,
        }
    ]
