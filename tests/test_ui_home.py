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
