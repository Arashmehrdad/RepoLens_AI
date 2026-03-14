"""Tests for document loading and path metadata."""

from pathlib import Path

from app.ingestion.document_loader import load_documents, load_documents_with_stats


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


def test_load_documents_marks_examples_ci_and_package_config(tmp_path: Path):
    """Metadata flags should cover example code, CI files, and package config."""
    repo_root = tmp_path / "repo"
    example_path = repo_root / "examples" / "demo.py"
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"
    package_path = repo_root / "pyproject.toml"
    release_note_path = repo_root / "docs" / "releases" / "v0.6.0.md"

    workflow_path.parent.mkdir(parents=True)
    example_path.parent.mkdir(parents=True)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    release_note_path.parent.mkdir(parents=True, exist_ok=True)
    example_path.write_text("print('demo')", encoding="utf-8")
    workflow_path.write_text("name: release", encoding="utf-8")
    package_path.write_text("[project]\nname='repo'", encoding="utf-8")
    release_note_path.write_text("# v0.6.0 release notes", encoding="utf-8")

    documents = load_documents(
        [example_path, workflow_path, package_path, release_note_path],
        repo_root,
    )
    documents_by_path = {document["path"]: document for document in documents}

    assert documents_by_path["examples/demo.py"]["is_example_file"] is True
    assert documents_by_path[".github/workflows/release.yml"]["is_ci_file"] is True
    assert documents_by_path["pyproject.toml"]["is_package_config"] is True
    assert documents_by_path["pyproject.toml"]["is_version_file"] is True
    assert documents_by_path["docs/releases/v0.6.0.md"]["is_release_note"] is True


def test_load_documents_does_not_treat_demo_docs_as_ci_workflows(tmp_path: Path):
    """Demo docs should not be misclassified as real CI or workflow files."""
    repo_root = tmp_path / "repo"
    demo_doc_path = repo_root / "docs" / "demo" / "release-workflow.md"

    demo_doc_path.parent.mkdir(parents=True)
    demo_doc_path.write_text("# Release demo", encoding="utf-8")

    documents = load_documents([demo_doc_path], repo_root)

    assert documents[0]["is_example_file"] is True
    assert documents[0]["is_workflow"] is False
    assert documents[0]["is_ci_file"] is False
    assert documents[0]["is_release_note"] is False


def test_load_documents_skips_non_utf8_files(tmp_path: Path):
    """Binary or undecodable files should be ignored instead of failing ingestion."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    binary_path = repo_root / "README.md"
    binary_path.write_bytes(b"\xff\xfe\x00\x00")

    documents = load_documents([binary_path], repo_root)

    assert documents == []


def test_load_documents_with_stats_reports_skip_reasons(tmp_path: Path):
    """Document loading should report why files were skipped."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    valid_path = repo_root / "README.md"
    binary_path = repo_root / "broken.txt"
    empty_path = repo_root / "EMPTY.md"
    valid_path.write_text("# RepoLens", encoding="utf-8")
    binary_path.write_bytes(b"\xff\xfe\x00\x00")
    empty_path.write_text("   \n", encoding="utf-8")

    result = load_documents_with_stats([valid_path, binary_path, empty_path], repo_root)

    assert len(result["documents"]) == 1
    assert result["skipped_reasons"]["decode_error"] == 1
    assert result["skipped_reasons"]["empty_file"] == 1
