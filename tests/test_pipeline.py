"""Tests for the ingestion pipeline."""

from pathlib import Path

from app.core.errors import IngestionLimitError
from app.ingestion import pipeline
from app.ingestion.manifest import build_incremental_plan
from app.ingestion.state import build_repo_state


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


def test_build_incremental_plan_detects_added_changed_removed_and_unchanged_files():
    """Incremental planning should separate file additions, changes, removals, and hits."""
    existing_manifest = {
        "files": {
            "README.md": {"file_hash": "same"},
            "old.py": {"file_hash": "gone"},
            "app/api/main.py": {"file_hash": "before"},
        }
    }
    documents = [
        {"path": "README.md", "content_hash": "same"},
        {"path": "app/api/main.py", "content_hash": "after"},
        {"path": "docker-compose.yml", "content_hash": "new"},
    ]

    plan = build_incremental_plan(existing_manifest, documents)

    assert plan["added_paths"] == ["docker-compose.yml"]
    assert plan["changed_paths"] == ["app/api/main.py"]
    assert plan["removed_paths"] == ["old.py"]
    assert plan["unchanged_paths"] == ["README.md"]


def test_incremental_reindex_removes_stale_chunks_for_deleted_files(monkeypatch, tmp_path: Path):
    """Incremental re-ingestion should delete stale vector chunks for removed files."""
    state = build_repo_state("https://github.com/example/repo", repo_path=tmp_path / "repo")
    documents = [
        {
            "content": "# RepoLens",
            "content_hash": "same-readme",
            "byte_size": 10,
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
            "is_example_file": False,
            "is_ci_file": False,
            "is_package_config": False,
            "is_tutorial_doc": False,
        }
    ]
    existing_manifest = {
        "files": {
            "README.md": {
                "path": "README.md",
                "file_hash": "same-readme",
                "size": 10,
                "chunk_ids": ["README.md::chunk_0"],
                "flags": {"is_readme": True},
            },
            "old.py": {
                "path": "old.py",
                "file_hash": "old-hash",
                "size": 20,
                "chunk_ids": ["old.py::chunk_0", "old.py::chunk_1"],
                "flags": {"is_app_entry": False},
            },
        }
    }
    final_manifest = {
        "files": {
            "README.md": existing_manifest["files"]["README.md"],
        }
    }
    removed_chunk_ids = []

    monkeypatch.setattr(
        pipeline,
        "chunk_documents",
        lambda current_documents, chunk_size, chunk_overlap: [],
    )
    monkeypatch.setattr(
        pipeline,
        "remove_chunks",
        lambda chunk_ids, collection_name: removed_chunk_ids.extend(chunk_ids) or len(chunk_ids),
    )
    monkeypatch.setattr(pipeline, "upsert_chunks", lambda chunks, collection_name: 0)
    monkeypatch.setattr(
        pipeline,
        "save_ingestion_manifest",
        lambda **kwargs: tmp_path / "manifest.json",
    )
    monkeypatch.setattr(pipeline, "load_manifest_for_state", lambda current_state: final_manifest)

    result = pipeline._incremental_reindex(
        state=state,
        documents=documents,
        discovery={"files": [tmp_path / "README.md"], "total_bytes": 10, "skipped_reasons": {}},
        document_result={"documents": documents, "skipped_reasons": {}},
        existing_manifest=existing_manifest,
    )

    assert removed_chunk_ids == ["old.py::chunk_0", "old.py::chunk_1"]
    assert result["incremental_stats"]["files_removed"] == 1
    assert result["incremental_stats"]["chunks_removed"] == 2
