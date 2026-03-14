"""Tests for Streamlit UI configuration helpers."""

from types import SimpleNamespace

from app.ui import home


def test_get_api_base_url_uses_env_value(monkeypatch):
    """The UI should respect the configured API base URL."""
    monkeypatch.setattr(home, "load_environment", lambda: None)
    monkeypatch.setenv("REPOLENS_API_BASE_URL", "https://api.example.com/")

    assert home.get_api_base_url() == "https://api.example.com"


def test_get_api_base_url_falls_back_to_local_default(monkeypatch):
    """The UI should keep a safe local default when no env var is set."""
    monkeypatch.setattr(home, "load_environment", lambda: None)
    monkeypatch.delenv("REPOLENS_API_BASE_URL", raising=False)

    assert home.get_api_base_url() == "http://127.0.0.1:8000"


def test_build_status_banner_handles_fallback_and_errors():
    """UI status banners should distinguish fallback, refusal, and error outcomes."""
    fallback_tone, fallback_message = home.build_status_banner(
        {"outcome": "fallback_answered", "confidence": "medium", "error_message": "missing key"}
    )
    error_tone, error_message = home.build_status_banner(
        {"outcome": "error", "confidence": "low", "error_message": "retrieval failed"}
    )

    assert fallback_tone == "warning"
    assert "missing key" in fallback_message
    assert error_tone == "error"
    assert "retrieval failed" in error_message


def test_extract_error_details_handles_structured_api_errors():
    """UI error parsing should unpack structured FastAPI error payloads."""
    response = SimpleNamespace(
        json=lambda: {"detail": {"error_code": "clone_failed", "error_message": "bad url"}},
        text="bad url",
    )

    error_code, error_message = home.extract_error_details(response)

    assert error_code == "clone_failed"
    assert error_message == "bad url"


def test_build_compare_status_banner_handles_success_and_weak_results():
    """Compare banners should distinguish strong and weak grounded comparisons."""
    success_tone, success_message = home.build_compare_status_banner(
        {"outcome": "compared", "confidence": "high"}
    )
    weak_tone, weak_message = home.build_compare_status_banner(
        {"outcome": "weak_compare", "confidence": "medium"}
    )

    assert success_tone == "success"
    assert "high confidence" in success_message
    assert weak_tone == "warning"
    assert "weak grounded evidence" in weak_message


def test_build_compare_request_payload_normalizes_optional_fields():
    """Compare payload helpers should normalize blank refs and queries to None."""
    payload = home.build_compare_request_payload(
        repo_url_a=" https://github.com/example/a ",
        repo_url_b=" https://github.com/example/b ",
        ref_a=" main ",
        ref_b=" ",
        query=" ",
        mode="release_diff",
    )

    assert payload == {
        "repo_url_a": "https://github.com/example/a",
        "repo_url_b": "https://github.com/example/b",
        "ref_a": "main",
        "ref_b": None,
        "query": None,
        "mode": "release_diff",
    }


def test_summarize_regression_versions_builds_table_rows():
    """Regression summaries should be converted into UI-friendly rows."""
    rows = home.summarize_regression_versions(
        {
            "versions": [
                {
                    "version": "v0.6.0",
                    "run_count": 2,
                    "latest_pass_rate": 1.0,
                    "latest_relevance_proxy_score": 0.9,
                    "latest_citation_correctness": 1.0,
                    "latest_refusal_correctness": 1.0,
                    "latest_latency_avg_ms": 25.4,
                }
            ]
        }
    )

    assert rows == [
        {
            "version": "v0.6.0",
            "runs": 2,
            "latest_pass_rate": 1.0,
            "latest_relevance": 0.9,
            "latest_citation": 1.0,
            "latest_refusal": 1.0,
            "latest_latency_ms": 25.4,
        }
    ]
