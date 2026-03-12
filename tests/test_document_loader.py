"""Tests for document loading and path metadata."""

from pathlib import Path

from app.ingestion.document_loader import load_documents


def test_load_documents_adds_path_metadata(tmp_path: Path):
    """Loaded documents should include path-aware metadata used by retrieval."""
    repo_root = tmp_path / "repo"
    readme_path = repo_root / "README.md"
    main_path = repo_root / "app" / "api" / "main.py"
    settings_path = repo_root / "config" / "settings.yaml"

    main_path.parent.mkdir(parents=True)
    settings_path.parent.mkdir(parents=True)
    readme_path.write_text("# RepoLens", encoding="utf-8")
    main_path.write_text("app = object()", encoding="utf-8")
    settings_path.write_text("debug: true", encoding="utf-8")

    documents = load_documents([readme_path, main_path, settings_path], repo_root)
    documents_by_path = {document["path"]: document for document in documents}

    assert documents_by_path["README.md"]["is_readme"] is True
    assert documents_by_path["README.md"]["is_docs_update"] is True
    assert documents_by_path["app/api/main.py"]["is_api"] is True
    assert documents_by_path["app/api/main.py"]["is_app_entry"] is True
    assert documents_by_path["config/settings.yaml"]["is_config"] is True


def test_load_documents_marks_release_and_deployment_files(tmp_path: Path):
    """Release and deployment metadata flags should be attached during loading."""
    repo_root = tmp_path / "repo"
    changelog_path = repo_root / "CHANGELOG.md"
    compose_path = repo_root / "docker-compose.yml"

    repo_root.mkdir()
    changelog_path.write_text("# Release Notes", encoding="utf-8")
    compose_path.write_text("services: {}", encoding="utf-8")

    documents = load_documents([changelog_path, compose_path], repo_root)
    documents_by_path = {document["path"]: document for document in documents}

    assert documents_by_path["CHANGELOG.md"]["is_changelog"] is True
    assert documents_by_path["CHANGELOG.md"]["is_release_note"] is True
    assert documents_by_path["docker-compose.yml"]["is_deployment_file"] is True


def test_load_documents_skips_non_utf8_files(tmp_path: Path):
    """Binary or undecodable files should be ignored instead of failing ingestion."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    binary_path = repo_root / "README.md"
    binary_path.write_bytes(b"\xff\xfe\x00\x00")

    documents = load_documents([binary_path], repo_root)

    assert documents == []
