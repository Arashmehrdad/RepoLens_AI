"""Tests for API response compatibility."""

from fastapi.testclient import TestClient

from app.api import main as api_main
from app.core.errors import IngestionLimitError, RepoStateError
from app.ingestion.pipeline import build_collection_name


def test_ask_endpoint_preserves_existing_response_fields(monkeypatch):
    """The ask endpoint should keep answer/citations/confidence while adding trace data."""
    monkeypatch.setattr(
        api_main,
        "answer_question",
        lambda query, collection_name="repo_chunks", mode="onboarding": {
            "answer": "Use uvicorn.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "outcome": "answered",
            "error_code": None,
            "error_message": None,
            "retrieval_diagnostics": {"matched_intents": ["setup"]},
            "trace_summary": {
                "timestamp": "2026-03-12T12:00:00+00:00",
                "request_id": "req-123",
                "collection_name": "repo_chunks",
                "outcome": "answered",
                "confidence": "high",
                "error_code": None,
                "error_message": None,
                "request_latency_ms": 12.5,
                "retrieval_latency_ms": 4.1,
                "chunks_retrieved_count": 5,
                "chunks_after_cleaning_count": 3,
                "citations_count": 1,
                "top_paths": ["README.md"],
                "top_citations": ["README.md:12-28"],
                "query_intents": ["setup"],
                "retrieval_fetch_count": 12,
                "raw_results_count": 5,
            },
        },
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/ask",
            json={
                "query": "How do I run this project?",
                "collection_name": "repo_chunks",
                "mode": "onboarding",
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["answer"] == "Use uvicorn."
    assert payload["citations"] == ["README.md:12-28"]
    assert payload["confidence"] == "high"
    assert payload["outcome"] == "answered"
    assert payload["trace_summary"]["request_id"] == "req-123"
    assert payload["retrieval_diagnostics"]["matched_intents"] == ["setup"]


def test_health_endpoint_returns_ok():
    """The deployment health endpoint should return an OK status."""
    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_endpoint_returns_structured_limit_errors(monkeypatch):
    """Ingest failures should surface structured error codes and messages."""
    monkeypatch.setattr(
        api_main,
        "ingest_repository",
        lambda repo_url: (_ for _ in ()).throw(
            IngestionLimitError(
                "too many files",
                error_code="ingestion_no_supported_files",
                diagnostics={"selected_files": 0},
            )
        ),
    )

    with TestClient(api_main.app) as client:
        response = client.post("/ingest", json={"repo_url": "https://github.com/example/demo"})

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "ingestion_no_supported_files"
    assert response.json()["detail"]["error_message"] == "too many files"


def test_ingest_and_ask_use_the_same_repo_specific_collection(monkeypatch):
    """Ask should resolve the same normalized collection name created during ingest."""
    repo_url = "https://github.com/Arashmehrdad/RepoLens_AI.git/"
    expected_collection_name = build_collection_name(repo_url)
    observed_collections = []

    monkeypatch.setattr(
        api_main,
        "ingest_repository",
        lambda incoming_repo_url: {
            "repo_path": "D:/tmp/RepoLens_AI",
            "collection_name": build_collection_name(incoming_repo_url),
            "file_count": 10,
            "document_count": 9,
            "chunk_count": 18,
            "indexed_count": 18,
        },
    )

    def fake_answer_question(query, collection_name, mode="onboarding"):
        observed_collections.append(collection_name)
        assert collection_name == expected_collection_name
        return {
            "answer": "Use docker compose up --build.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "outcome": "answered",
            "error_code": None,
            "error_message": None,
            "retrieval_diagnostics": {"matched_intents": ["setup"], "raw_result_count": 3},
            "trace_summary": {
                "timestamp": "2026-03-12T12:00:00+00:00",
                "request_id": "req-456",
                "collection_name": expected_collection_name,
                "outcome": "answered",
                "confidence": "high",
                "error_code": None,
                "error_message": None,
                "request_latency_ms": 10.0,
                "retrieval_latency_ms": 3.5,
                "chunks_retrieved_count": 3,
                "chunks_after_cleaning_count": 2,
                "citations_count": 1,
                "top_paths": ["README.md"],
                "top_citations": ["README.md:12-28"],
                "query_intents": ["setup"],
                "retrieval_fetch_count": 12,
                "raw_results_count": 3,
            },
        }

    monkeypatch.setattr(api_main, "answer_question", fake_answer_question)

    with TestClient(api_main.app) as client:
        ingest_response = client.post("/ingest", json={"repo_url": repo_url})
        ask_response = client.post(
            "/ask",
            json={
                "query": "How do I run this project?",
                "repo_url": repo_url,
                "mode": "onboarding",
            },
        )

    assert ingest_response.status_code == 200
    assert ingest_response.json()["collection_name"] == expected_collection_name
    assert ask_response.status_code == 200
    assert observed_collections == [expected_collection_name]
    assert ask_response.json()["trace_summary"]["raw_results_count"] == 3


def test_ingest_endpoint_supports_ref_aware_repo_states(monkeypatch):
    """Ingest should accept refs and return state metadata for that repo snapshot."""
    repo_url = "https://github.com/example/repo"

    monkeypatch.setattr(
        api_main,
        "ingest_repository_state",
        lambda repo_url, ref=None: {
            "repo_path": "D:/tmp/repo",
            "collection_name": "repo_repo__v0_6_0_123abc",
            "file_count": 12,
            "document_count": 10,
            "chunk_count": 25,
            "indexed_count": 25,
            "ingestion_diagnostics": {"discovery": {"selected_files": 12}},
            "state": {
                "repo_url": repo_url,
                "repo_name": "repo",
                "normalized_repo_url": repo_url,
                "ref": ref,
                "state_id": "repo__v0_6_0__123abc",
                "collection_name": "repo_repo__v0_6_0_123abc",
                "repo_path": "D:/tmp/repo",
                "commit_sha": "abc123",
                "manifest_path": "D:/tmp/manifest.json",
            },
            "manifest_path": "D:/tmp/manifest.json",
            "incremental_stats": {"incremental_used": False},
        },
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/ingest",
            json={"repo_url": repo_url, "ref": "v0.6.0"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["state"]["ref"] == "v0.6.0"
    assert payload["manifest_path"] == "D:/tmp/manifest.json"
    assert payload["incremental_stats"]["incremental_used"] is False


def test_compare_endpoint_returns_grounded_multi_repo_response(monkeypatch):
    """Compare should expose grounded diff summaries without changing ask behavior."""
    monkeypatch.setattr(
        api_main,
        "compare_repo_states",
        lambda **kwargs: {
            "answer": "State B adds a release workflow.",
            "citations": ["A: README.md:10-20", "B: .github/workflows/release.yml:1-12"],
            "confidence": "high",
            "outcome": "compared",
            "state_a": {
                "repo_url": kwargs["repo_url_a"],
                "repo_name": "repo",
                "normalized_repo_url": kwargs["repo_url_a"],
                "ref": kwargs["ref_a"] or "default",
                "state_id": "state-a",
                "collection_name": "collection-a",
                "repo_path": "D:/tmp/a",
                "commit_sha": None,
                "manifest_path": "D:/tmp/a.json",
            },
            "state_b": {
                "repo_url": kwargs["repo_url_b"],
                "repo_name": "repo",
                "normalized_repo_url": kwargs["repo_url_b"],
                "ref": kwargs["ref_b"] or "default",
                "state_id": "state-b",
                "collection_name": "collection-b",
                "repo_path": "D:/tmp/b",
                "commit_sha": None,
                "manifest_path": "D:/tmp/b.json",
            },
            "changed_files": ["README.md"],
            "added_files": [".github/workflows/release.yml"],
            "removed_files": [],
            "setup_impact": ["README.md"],
            "deployment_impact": [".github/workflows/release.yml"],
            "ci_cd_impact": [".github/workflows/release.yml"],
            "package_impact": [],
            "api_runtime_impact": [],
            "diagnostics": {"compare_mode": kwargs["mode"]},
            "state_a_citations": ["README.md:10-20"],
            "state_b_citations": [".github/workflows/release.yml:1-12"],
            "state_a_evidence": [],
            "state_b_evidence": [],
        },
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/compare",
            json={
                "repo_url_a": "https://github.com/example/repo",
                "repo_url_b": "https://github.com/example/repo",
                "ref_a": "v0.5.0",
                "ref_b": "v0.6.0",
                "query": "What changed?",
                "mode": "compare",
            },
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["outcome"] == "compared"
    assert payload["added_files"] == [".github/workflows/release.yml"]
    assert payload["diagnostics"]["compare_mode"] == "compare"


def test_release_diff_endpoint_forces_release_diff_mode(monkeypatch):
    """Release-diff endpoint should route compare calls through release prioritization."""
    observed_modes = []

    def fake_compare_repo_states(**kwargs):
        observed_modes.append(kwargs["mode"])
        return {
            "answer": "Release notes changed.",
            "citations": [],
            "confidence": "medium",
            "outcome": "weak_compare",
            "state_a": None,
            "state_b": None,
            "changed_files": [],
            "added_files": [],
            "removed_files": [],
            "setup_impact": [],
            "deployment_impact": [],
            "ci_cd_impact": [],
            "package_impact": [],
            "api_runtime_impact": [],
            "diagnostics": {"compare_mode": kwargs["mode"]},
            "state_a_citations": [],
            "state_b_citations": [],
            "state_a_evidence": [],
            "state_b_evidence": [],
        }

    monkeypatch.setattr(api_main, "compare_repo_states", fake_compare_repo_states)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/release-diff",
            json={
                "repo_url_a": "https://github.com/example/repo",
                "repo_url_b": "https://github.com/example/repo",
                "ref_a": "v0.5.0",
                "ref_b": "v0.6.0",
            },
        )

    assert response.status_code == 200
    assert observed_modes == ["release_diff"]


def test_eval_regressions_endpoint_returns_structured_dashboard(monkeypatch):
    """Regression endpoint should expose version summaries and metric series."""
    monkeypatch.setattr(
        api_main,
        "aggregate_regressions",
        lambda versions=None: {
            "available_versions": ["v0.5.0", "v0.6.0"],
            "selected_versions": versions or ["v0.5.0", "v0.6.0"],
            "versions": [{"version": "v0.6.0", "run_count": 1}],
            "runs": [{"version": "v0.6.0", "timestamp": "20260313T120000Z"}],
            "metric_series": [{"version": "v0.6.0", "pass_rate": 1.0}],
        },
    )

    with TestClient(api_main.app) as client:
        response = client.get("/eval-regressions", params={"versions": "v0.6.0"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["available_versions"] == ["v0.5.0", "v0.6.0"]
    assert payload["selected_versions"] == ["v0.6.0"]


def test_review_report_endpoint_returns_export_paths(monkeypatch):
    """Review report endpoint should return deterministic export artifacts."""
    monkeypatch.setattr(
        api_main,
        "export_review_report",
        lambda **kwargs: {
            "report_id": "release_diff_abcd1234",
            "mode": kwargs["mode"],
            "json_path": "D:/tmp/report.json",
            "markdown_path": "D:/tmp/report.md",
            "markdown": "# Report\n",
            "report": {"summary": "State B adds a release workflow."},
        },
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/review-report",
            json={
                "repo_url_a": "https://github.com/example/repo",
                "repo_url_b": "https://github.com/example/repo",
                "ref_a": "v0.5.0",
                "ref_b": "v0.6.0",
                "mode": "release_diff",
            },
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["report_id"] == "release_diff_abcd1234"
    assert payload["mode"] == "release_diff"
    assert payload["markdown_path"] == "D:/tmp/report.md"


def test_compare_endpoint_returns_structured_repo_state_errors(monkeypatch):
    """Compare failures should surface structured HTTP errors."""
    monkeypatch.setattr(
        api_main,
        "compare_repo_states",
        lambda **kwargs: (_ for _ in ()).throw(
            RepoStateError(
                "State manifest missing",
                error_code="repo_state_missing_manifest",
                diagnostics={"state_id": "missing"},
            )
        ),
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/compare",
            json={
                "repo_url_a": "https://github.com/example/repo",
                "repo_url_b": "https://github.com/example/repo",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "repo_state_missing_manifest"
