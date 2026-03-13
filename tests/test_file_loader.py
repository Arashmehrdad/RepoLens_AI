"""Tests for repository file discovery."""

from pathlib import Path

from app.ingestion import file_loader


def test_list_supported_files_includes_supported_and_special_files(tmp_path: Path):
    """Supported files and always-included filenames should be discovered."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "README.md").write_text("# RepoLens", encoding="utf-8")
    (repo_root / "app.py").write_text("print('ok')", encoding="utf-8")
    (repo_root / "Dockerfile").write_text("FROM python:3.11", encoding="utf-8")
    (repo_root / "requirements.txt").write_text("fastapi", encoding="utf-8")

    files = file_loader.list_supported_files(repo_root)
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

    files = file_loader.list_supported_files(repo_root)
    relative_paths = {path.relative_to(repo_root).as_posix() for path in files}

    assert "src/main.py" in relative_paths
    assert "node_modules/package.json" not in relative_paths
    assert "__pycache__/cached.py" not in relative_paths


def test_discover_files_reports_skip_reasons_and_limit_hits(tmp_path: Path, monkeypatch):
    """Discovery should report why noisy or oversized files were skipped."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    kept_path = repo_root / "README.md"
    big_path = repo_root / "large.md"
    binary_path = repo_root / "image.png"
    minified_path = repo_root / "bundle.min.js"
    kept_path.write_text("# RepoLens", encoding="utf-8")
    big_path.write_text("x" * 80, encoding="utf-8")
    binary_path.write_bytes(b"\x89PNG")
    minified_path.write_text("var a=1;", encoding="utf-8")

    monkeypatch.setattr(file_loader, "MAX_FILE_SIZE_BYTES", 32)

    result = file_loader.discover_files(repo_root)
    relative_paths = {path.relative_to(repo_root).as_posix() for path in result["files"]}

    assert relative_paths == {"README.md"}
    assert result["skipped_reasons"]["max_file_size_exceeded"] == 1
    assert result["skipped_reasons"]["denylisted_extension"] == 1
    assert result["skipped_reasons"]["generated_asset"] == 1


def test_discover_files_skips_generated_eval_and_trace_artifacts(tmp_path: Path):
    """Generated evaluation and trace files should not be ingested as evidence."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "README.md").write_text("# RepoLens", encoding="utf-8")
    (repo_root / "eval_results.json").write_text("{}", encoding="utf-8")
    (repo_root / "logs").mkdir()
    (repo_root / "logs" / "traces.jsonl").write_text("{}", encoding="utf-8")

    result = file_loader.discover_files(repo_root)
    relative_paths = {path.relative_to(repo_root).as_posix() for path in result["files"]}

    assert relative_paths == {"README.md"}
    assert result["skipped_reasons"]["noisy_filename"] == 1
    assert result["skipped_reasons"]["ignored_directory"] == 1
