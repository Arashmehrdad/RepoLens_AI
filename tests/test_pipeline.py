"""Tests for the ingestion pipeline."""

from pathlib import Path

from app.core.errors import IngestionLimitError
from app.ingestion import pipeline


def test_ingest_repository_returns_ingestion_diagnostics(monkeypatch, tmp_path: Path):
    """Ingestion should report discovery and loading diagnostics."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    file_path = repo_path / "README.md"
    file_path.write_text("# RepoLens", encoding="utf-8")

    monkeypatch.setattr(pipeline, "clone_repo", lambda repo_url: repo_path)
    monkeypatch.setattr(
        pipeline,
        "discover_files",
        lambda current_repo_path: {
            "files": [file_path],
            "total_bytes": 10,
            "skipped_reasons": {"unsupported_extension": 2},
        },
    )
    monkeypatch.setattr(
        pipeline,
        "load_documents_with_stats",
        lambda file_paths, current_repo_path: {
            "documents": [
                {
                    "content": "# RepoLens",
                    "path": "README.md",
                    "path_lower": "readme.md",
                    "filename": "README.md",
                    "filename_lower": "readme.md",
                    "suffix": ".md",
                    "stem": "readme",
                    "parent_dirs": [],
                    "parent_dirs_joined": "",
                    "depth": 1,
                    "is_readme": True,
                    "is_config": False,
                    "is_docker": False,
                    "is_compose": False,
                    "is_api": False,
                    "is_app_entry": False,
                    "is_training": False,
                    "is_workflow": False,
                    "is_dependency_file": False,
                    "is_changelog": False,
                    "is_release_note": False,
                    "is_version_file": False,
                    "is_deployment_file": False,
                    "is_docs_update": True,
                    "is_architecture_doc": False,
                    "is_test_file": False,
                }
            ],
            "skipped_reasons": {"decode_error": 1},
        },
    )
    monkeypatch.setattr(pipeline, "chunk_documents", lambda documents, chunk_size, chunk_overlap: [{"path": "README.md", "chunk_index": 0, "content": "x"}])
    monkeypatch.setattr(pipeline, "index_chunks", lambda chunks, collection_name: 1)

    result = pipeline.ingest_repository("https://github.com/example/repo")

    assert result["collection_name"] == "repo_repo"
    assert result["ingestion_diagnostics"]["discovery"]["selected_files"] == 1
    assert result["ingestion_diagnostics"]["loading"]["skipped_reasons"]["decode_error"] == 1


def test_ingest_repository_raises_limit_error_when_no_documents(monkeypatch, tmp_path: Path):
    """Ingestion should fail cleanly when no files survive the configured limits."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    monkeypatch.setattr(pipeline, "clone_repo", lambda repo_url: repo_path)
    monkeypatch.setattr(
        pipeline,
        "discover_files",
        lambda current_repo_path: {
            "files": [],
            "total_bytes": 0,
            "skipped_reasons": {"max_files_exceeded": 10},
        },
    )
    monkeypatch.setattr(
        pipeline,
        "load_documents_with_stats",
        lambda file_paths, current_repo_path: {"documents": [], "skipped_reasons": {}},
    )

    try:
        pipeline.ingest_repository("https://github.com/example/repo")
    except IngestionLimitError as exc:
        assert exc.error_code == "ingestion_no_supported_files"
    else:
        raise AssertionError("Expected IngestionLimitError to be raised")


def test_ingest_repository_uses_local_file_url_without_cloning(
    monkeypatch,
    tmp_path: Path,
):
    """Local file URLs should ingest the working tree directly instead of cloning."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    file_path = repo_path / "README.md"
    file_path.write_text("# RepoLens", encoding="utf-8")

    def fail_clone(repo_url):
        raise AssertionError(f"clone_repo should not be called for {repo_url}")

    monkeypatch.setattr(pipeline, "clone_repo", fail_clone)
    monkeypatch.setattr(
        pipeline,
        "discover_files",
        lambda current_repo_path: {
            "files": [file_path],
            "total_bytes": 10,
            "skipped_reasons": {},
        },
    )
    monkeypatch.setattr(
        pipeline,
        "load_documents_with_stats",
        lambda file_paths, current_repo_path: {
            "documents": [
                {
                    "content": "# RepoLens",
                    "path": "README.md",
                    "path_lower": "readme.md",
                    "filename": "README.md",
                    "filename_lower": "readme.md",
                    "suffix": ".md",
                    "stem": "readme",
                    "parent_dirs": [],
                    "parent_dirs_joined": "",
                    "depth": 1,
                    "is_readme": True,
                    "is_config": False,
                    "is_docker": False,
                    "is_compose": False,
                    "is_api": False,
                    "is_app_entry": False,
                    "is_training": False,
                    "is_workflow": False,
                    "is_dependency_file": False,
                    "is_changelog": False,
                    "is_release_note": False,
                    "is_version_file": False,
                    "is_deployment_file": False,
                    "is_docs_update": True,
                    "is_architecture_doc": False,
                    "is_test_file": False,
                }
            ],
            "skipped_reasons": {},
        },
    )
    monkeypatch.setattr(
        pipeline,
        "chunk_documents",
        lambda documents, chunk_size, chunk_overlap: [
            {"path": "README.md", "chunk_index": 0, "content": "x"}
        ],
    )
    monkeypatch.setattr(pipeline, "index_chunks", lambda chunks, collection_name: 1)

    result = pipeline.ingest_repository(f"file:///{repo_path.as_posix()}")

    assert result["repo_path"] == str(repo_path.resolve())
    assert result["collection_name"] == "repo_repo"
