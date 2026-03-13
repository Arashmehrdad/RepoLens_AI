"""Tests for the LLM writer."""

from types import SimpleNamespace

from app.core.errors import LLMDependencyError, LLMInvocationError
from app.generation import llm_writer


def test_write_grounded_answer_builds_prompt_from_top_three_chunks(monkeypatch):
    """The LLM writer should use the first three chunks and strip the model output."""
    calls = []

    class FakeModels:
        """Model stub that records generate calls."""

        def generate_content(self, model, contents):
            calls.append({"model": model, "contents": contents})
            return SimpleNamespace(text="  Grounded answer.  ")

    class FakeClient:
        """Client stub that exposes fake model methods."""

        def __init__(self, api_key):
            self.api_key = api_key
            self.models = FakeModels()

    monkeypatch.setattr(llm_writer, "_get_genai_client", lambda: FakeClient("test-key"))

    chunks = [
        {"content": "one", "metadata": {"path": "README.md", "start_line": 12, "end_line": 28, "section": "Setup", "symbol": ""}},
        {"content": "two", "metadata": {"path": "app/api/main.py", "start_line": 5, "end_line": 31, "section": "", "symbol": "ask_question"}},
        {"content": "three", "metadata": {"path": "requirements.txt", "start_line": 1, "end_line": 10, "section": "", "symbol": ""}},
        {"content": "four", "metadata": {"path": "ignored.py", "start_line": 1, "end_line": 1, "section": "", "symbol": ""}},
    ]

    answer = llm_writer.write_grounded_answer("How do I run this project?", chunks)

    assert answer == "Grounded answer."
    assert calls[0]["model"] == llm_writer.MODEL_NAME
    assert "FILE: README.md:12-28" in calls[0]["contents"]
    assert "SECTION: Setup" in calls[0]["contents"]
    assert "FILE: app/api/main.py:5-31" in calls[0]["contents"]
    assert "SYMBOL: ask_question" in calls[0]["contents"]
    assert "FILE: requirements.txt:1-10" in calls[0]["contents"]
    assert "ignored.py" not in calls[0]["contents"]


def test_get_genai_client_requires_api_key(monkeypatch):
    """Missing GEMINI_API_KEY should raise a structured dependency error."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    try:
        llm_writer._get_genai_client()
    except LLMDependencyError as exc:
        assert exc.error_code == "llm_missing_api_key"
    else:
        raise AssertionError("Expected LLMDependencyError to be raised")


def test_get_genai_client_requires_google_genai_dependency(monkeypatch):
    """Missing google-genai should raise a structured dependency error."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        llm_writer.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("missing")) if name == "google.genai" else None,
    )

    try:
        llm_writer._get_genai_client()
    except LLMDependencyError as exc:
        assert exc.error_code == "llm_dependency_missing"
    else:
        raise AssertionError("Expected LLMDependencyError to be raised")


def test_write_grounded_answer_wraps_model_failures(monkeypatch):
    """Model invocation failures should be raised as structured LLM errors."""

    class FakeModels:
        """Model stub that fails on generate calls."""

        def generate_content(self, model, contents):
            raise RuntimeError(f"failed: {model} / {contents}")

    class FakeClient:
        """Client stub that exposes the failing model methods."""

        def __init__(self):
            self.models = FakeModels()

    monkeypatch.setattr(llm_writer, "_get_genai_client", lambda: FakeClient())

    chunks = [
        {"content": "one", "metadata": {"path": "README.md", "start_line": 12, "end_line": 28, "section": "Setup", "symbol": ""}},
    ]

    try:
        llm_writer.write_grounded_answer("How do I run this project?", chunks)
    except LLMInvocationError as exc:
        assert exc.error_code == "llm_invocation_failed"
    else:
        raise AssertionError("Expected LLMInvocationError to be raised")
