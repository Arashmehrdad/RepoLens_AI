"""Tests for the LLM writer."""

from types import SimpleNamespace

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

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm_writer.genai, "Client", FakeClient)

    chunks = [
        {"content": "one", "metadata": {"path": "README.md"}},
        {"content": "two", "metadata": {"path": "app/api/main.py"}},
        {"content": "three", "metadata": {"path": "requirements.txt"}},
        {"content": "four", "metadata": {"path": "ignored.py"}},
    ]

    answer = llm_writer.write_grounded_answer("How do I run this project?", chunks)

    assert answer == "Grounded answer."
    assert calls[0]["model"] == llm_writer.MODEL_NAME
    assert "FILE: README.md" in calls[0]["contents"]
    assert "FILE: app/api/main.py" in calls[0]["contents"]
    assert "FILE: requirements.txt" in calls[0]["contents"]
    assert "ignored.py" not in calls[0]["contents"]
