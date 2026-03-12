"""Tests for Streamlit UI configuration helpers."""

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
