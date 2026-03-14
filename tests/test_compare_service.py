"""Tests for grounded repo-state comparison helpers."""

from pathlib import Path

from app.comparison import service
from app.ingestion.state import build_repo_state


def _build_manifest_file(path: str, file_hash: str, chunk_id: str, **flags) -> dict:
    """Return one manifest entry used by comparison tests."""
    return {
        "path": path,
        "file_hash": file_hash,
        "size": 100,
        "chunk_ids": [chunk_id],
        "flags": flags,
    }


def _build_ingest_payload(repo_url: str, ref: str, repo_path: Path) -> dict:
    """Return a minimal ingestion payload for one repo state."""
    state = build_repo_state(repo_url=repo_url, ref=ref, repo_path=repo_path)
    return {
        "repo_path": str(repo_path),
        "collection_name": state.collection_name,
        "file_count": 4,
        "document_count": 4,
        "chunk_count": 4,
        "indexed_count": 4,
        "state": state.to_dict(),
        "manifest_path": state.manifest_path,
        "incremental_stats": {"incremental_used": True, "files_changed": 1},
        "ingestion_diagnostics": {
            "discovery": {
                "selected_files": 4,
                "total_bytes": 1000,
                "skipped_reasons": {
                    "generated_asset": 2,
                    "unsupported_extension": 1,
                },
            }
        },
    }


def test_compare_repo_states_reports_changed_added_removed_and_impacts(
    monkeypatch,
    tmp_path: Path,
):
    """Compare mode should surface grounded file diffs and impact buckets."""
    repo_url = "https://github.com/example/repolens"
    payload_a = _build_ingest_payload(repo_url, "v0.5.0", tmp_path / "state-a")
    payload_b = _build_ingest_payload(repo_url, "v0.6.0", tmp_path / "state-b")
    state_a = build_repo_state(repo_url, ref="v0.5.0", repo_path=tmp_path / "state-a")
    state_b = build_repo_state(repo_url, ref="v0.6.0", repo_path=tmp_path / "state-b")

    manifest_a = {
        "state": state_a.to_dict(),
        "files": {
            "README.md": _build_manifest_file(
                "README.md",
                "hash-a-readme",
                "README.md::chunk_0",
                is_readme=True,
                is_docs_update=True,
                is_config=False,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=False,
                is_docker=False,
                is_compose=False,
                is_workflow=False,
                is_ci_file=False,
                is_api=False,
                is_app_entry=False,
                is_tutorial_doc=True,
            ),
            "Dockerfile": _build_manifest_file(
                "Dockerfile",
                "hash-a-docker",
                "Dockerfile::chunk_0",
                is_readme=False,
                is_docs_update=False,
                is_config=False,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=True,
                is_docker=True,
                is_compose=False,
                is_workflow=False,
                is_ci_file=False,
                is_api=False,
                is_app_entry=False,
                is_tutorial_doc=False,
            ),
            "app/api/main.py": _build_manifest_file(
                "app/api/main.py",
                "hash-a-main",
                "app/api/main.py::chunk_0",
                is_readme=False,
                is_docs_update=False,
                is_config=False,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=False,
                is_docker=False,
                is_compose=False,
                is_workflow=False,
                is_ci_file=False,
                is_api=True,
                is_app_entry=True,
                is_tutorial_doc=False,
            ),
        },
    }
    manifest_b = {
        "state": state_b.to_dict(),
        "files": {
            "README.md": _build_manifest_file(
                "README.md",
                "hash-b-readme",
                "README.md::chunk_0",
                is_readme=True,
                is_docs_update=True,
                is_config=False,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=False,
                is_docker=False,
                is_compose=False,
                is_workflow=False,
                is_ci_file=False,
                is_api=False,
                is_app_entry=False,
                is_tutorial_doc=True,
            ),
            "docker-compose.yml": _build_manifest_file(
                "docker-compose.yml",
                "hash-b-compose",
                "docker-compose.yml::chunk_0",
                is_readme=False,
                is_docs_update=False,
                is_config=True,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=True,
                is_docker=False,
                is_compose=True,
                is_workflow=False,
                is_ci_file=False,
                is_api=False,
                is_app_entry=False,
                is_tutorial_doc=False,
            ),
            ".github/workflows/release.yml": _build_manifest_file(
                ".github/workflows/release.yml",
                "hash-b-workflow",
                ".github/workflows/release.yml::chunk_0",
                is_readme=False,
                is_docs_update=False,
                is_config=True,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=True,
                is_docker=False,
                is_compose=False,
                is_workflow=True,
                is_ci_file=True,
                is_api=False,
                is_app_entry=False,
                is_tutorial_doc=False,
            ),
            "app/api/main.py": _build_manifest_file(
                "app/api/main.py",
                "hash-b-main",
                "app/api/main.py::chunk_0",
                is_readme=False,
                is_docs_update=False,
                is_config=False,
                is_dependency_file=False,
                is_package_config=False,
                is_release_note=False,
                is_changelog=False,
                is_version_file=False,
                is_deployment_file=False,
                is_docker=False,
                is_compose=False,
                is_workflow=False,
                is_ci_file=False,
                is_api=True,
                is_app_entry=True,
                is_tutorial_doc=False,
            ),
        },
    }
    chunks_by_id = {
        "README.md::chunk_0": {
            "id": "README.md::chunk_0",
            "content": "README setup changed for the new release.",
            "metadata": {
                "path": "README.md",
                "start_line": 10,
                "end_line": 24,
            },
        },
        "Dockerfile::chunk_0": {
            "id": "Dockerfile::chunk_0",
            "content": "Docker image definition was removed.",
            "metadata": {
                "path": "Dockerfile",
                "start_line": 1,
                "end_line": 12,
            },
        },
        "docker-compose.yml::chunk_0": {
            "id": "docker-compose.yml::chunk_0",
            "content": "Compose services were added for local deployment.",
            "metadata": {
                "path": "docker-compose.yml",
                "start_line": 1,
                "end_line": 18,
            },
        },
        ".github/workflows/release.yml::chunk_0": {
            "id": ".github/workflows/release.yml::chunk_0",
            "content": "Release workflow publishes deployment artifacts.",
            "metadata": {
                "path": ".github/workflows/release.yml",
                "start_line": 2,
                "end_line": 20,
            },
        },
        "app/api/main.py::chunk_0": {
            "id": "app/api/main.py::chunk_0",
            "content": "API startup behavior changed between releases.",
            "metadata": {
                "path": "app/api/main.py",
                "start_line": 20,
                "end_line": 42,
            },
        },
    }

    monkeypatch.setattr(
        service,
        "ingest_repository_state",
        lambda repo_url, ref=None: payload_a if ref == "v0.5.0" else payload_b,
    )
    monkeypatch.setattr(
        service,
        "load_manifest_for_state",
        lambda state: manifest_a if state.ref == "v0.5.0" else manifest_b,
    )
    monkeypatch.setattr(
        service,
        "get_chunks_by_ids",
        lambda collection_name, chunk_ids: [
            chunks_by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in chunks_by_id
        ],
    )

    result = service.compare_repo_states(
        repo_url_a=repo_url,
        repo_url_b=repo_url,
        ref_a="v0.5.0",
        ref_b="v0.6.0",
        query="What changed and what affects deployment?",
        mode="compare",
    )

    assert result["outcome"] == "compared"
    assert "README.md" in result["changed_files"]
    assert "app/api/main.py" in result["changed_files"]
    assert "docker-compose.yml" in result["added_files"]
    assert "Dockerfile" in result["removed_files"]
    assert "docker-compose.yml" in result["deployment_impact"]
    assert ".github/workflows/release.yml" in result["ci_cd_impact"]
    assert "app/api/main.py" in result["api_runtime_impact"]
    assert result["citations"][0].startswith("A: ")
    assert any(citation.startswith("B: ") for citation in result["citations"])
    assert result["diagnostics"]["noisy_files"]["state_a"]["generated_asset"] == 2


def test_release_diff_prioritizes_changelog_and_release_signals(monkeypatch, tmp_path: Path):
    """Release diff mode should prioritize changelogs above generic docs changes."""
    repo_url = "https://github.com/example/repolens"
    payload_a = _build_ingest_payload(repo_url, "v0.5.0", tmp_path / "state-a")
    payload_b = _build_ingest_payload(repo_url, "v0.6.0", tmp_path / "state-b")
    state_a = build_repo_state(repo_url, ref="v0.5.0", repo_path=tmp_path / "state-a")
    state_b = build_repo_state(repo_url, ref="v0.6.0", repo_path=tmp_path / "state-b")
    manifest_a = {
        "state": state_a.to_dict(),
        "files": {
            "README.md": _build_manifest_file(
                "README.md",
                "hash-old-readme",
                "README.md::chunk_0",
                is_readme=True,
                is_docs_update=True,
                is_changelog=False,
                is_release_note=False,
                is_version_file=False,
                is_package_config=False,
                is_workflow=False,
                is_ci_file=False,
                is_deployment_file=False,
                is_dependency_file=False,
                is_config=False,
                is_api=False,
                is_app_entry=False,
            ),
            "CHANGELOG.md": _build_manifest_file(
                "CHANGELOG.md",
                "hash-old-changelog",
                "CHANGELOG.md::chunk_0",
                is_readme=False,
                is_docs_update=True,
                is_changelog=True,
                is_release_note=True,
                is_version_file=False,
                is_package_config=False,
                is_workflow=False,
                is_ci_file=False,
                is_deployment_file=False,
                is_dependency_file=False,
                is_config=False,
                is_api=False,
                is_app_entry=False,
            ),
        },
    }
    manifest_b = {
        "state": state_b.to_dict(),
        "files": {
            "README.md": _build_manifest_file(
                "README.md",
                "hash-new-readme",
                "README.md::chunk_0",
                is_readme=True,
                is_docs_update=True,
                is_changelog=False,
                is_release_note=False,
                is_version_file=False,
                is_package_config=False,
                is_workflow=False,
                is_ci_file=False,
                is_deployment_file=False,
                is_dependency_file=False,
                is_config=False,
                is_api=False,
                is_app_entry=False,
            ),
            "CHANGELOG.md": _build_manifest_file(
                "CHANGELOG.md",
                "hash-new-changelog",
                "CHANGELOG.md::chunk_0",
                is_readme=False,
                is_docs_update=True,
                is_changelog=True,
                is_release_note=True,
                is_version_file=False,
                is_package_config=False,
                is_workflow=False,
                is_ci_file=False,
                is_deployment_file=False,
                is_dependency_file=False,
                is_config=False,
                is_api=False,
                is_app_entry=False,
            ),
        },
    }

    monkeypatch.setattr(
        service,
        "ingest_repository_state",
        lambda repo_url, ref=None: payload_a if ref == "v0.5.0" else payload_b,
    )
    monkeypatch.setattr(
        service,
        "load_manifest_for_state",
        lambda state: manifest_a if state.ref == "v0.5.0" else manifest_b,
    )
    monkeypatch.setattr(service, "get_chunks_by_ids", lambda collection_name, chunk_ids: [])

    result = service.compare_repo_states(
        repo_url_a=repo_url,
        repo_url_b=repo_url,
        ref_a="v0.5.0",
        ref_b="v0.6.0",
        query="What changed from v0.5.0 to v0.6.0?",
        mode="release_diff",
    )

    assert result["diagnostics"]["prioritized_files"][0]["path"] == "CHANGELOG.md"
    assert result["diagnostics"]["release_diff_signals"]["is_changelog"] >= 1
