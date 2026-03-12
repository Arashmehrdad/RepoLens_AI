"""Tests for repository file discovery."""

from pathlib import Path

from app.ingestion.file_loader import list_supported_files


def test_list_supported_files_includes_supported_and_special_files(tmp_path: Path):
    """Supported files and always-included filenames should be discovered."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "README.md").write_text("# RepoLens", encoding="utf-8")
    (repo_root / "app.py").write_text("print('ok')", encoding="utf-8")
    (repo_root / "Dockerfile").write_text("FROM python:3.11", encoding="utf-8")
    (repo_root / "requirements.txt").write_text("fastapi", encoding="utf-8")

    files = list_supported_files(repo_root)
    relative_paths = {path.relative_to(repo_root).as_posix() for path in files}

    assert {"README.md", "app.py", "Dockerfile", "requirements.txt"} <= relative_paths


def test_list_supported_files_skips_ignored_directories(tmp_path: Path):
    """Files inside ignored directories should not be returned."""
    repo_root = tmp_path / "repo"
    node_modules_file = repo_root / "node_modules" / "package.json"
    cache_file = repo_root / "__pycache__" / "cached.py"
    kept_file = repo_root / "src" / "main.py"

    node_modules_file.parent.mkdir(parents=True)
    cache_file.parent.mkdir(parents=True)
    kept_file.parent.mkdir(parents=True)
    node_modules_file.write_text('{"name": "pkg"}', encoding="utf-8")
    cache_file.write_text("compiled", encoding="utf-8")
    kept_file.write_text("print('ok')", encoding="utf-8")

    files = list_supported_files(repo_root)
    relative_paths = {path.relative_to(repo_root).as_posix() for path in files}

    assert "src/main.py" in relative_paths
    assert "node_modules/package.json" not in relative_paths
    assert "__pycache__/cached.py" not in relative_paths
