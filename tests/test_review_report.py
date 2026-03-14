"""Tests for exportable compare review reports."""

import json
from pathlib import Path

from app.ingestion.state import build_repo_state
from app.reports import review_report


def test_export_review_report_writes_markdown_and_json(monkeypatch, tmp_path: Path):
    """Review report export should persist deterministic markdown and JSON files."""
    state_a = build_repo_state("https://github.com/example/repo", ref="v0.5.0")
    state_b = build_repo_state("https://github.com/example/repo", ref="v0.6.0")
    compare_result = {
        "answer": "State B adds deployment and release workflow changes.",
        "citations": ["A: README.md:10-20", "B: CHANGELOG.md:1-12"],
        "confidence": "high",
        "outcome": "compared",
        "state_a": state_a.to_dict(),
        "state_b": state_b.to_dict(),
        "changed_files": ["README.md"],
        "added_files": [".github/workflows/release.yml"],
        "removed_files": [],
        "setup_impact": ["README.md"],
        "deployment_impact": [".github/workflows/release.yml"],
        "ci_cd_impact": [".github/workflows/release.yml"],
        "package_impact": ["pyproject.toml"],
        "api_runtime_impact": ["app/api/main.py"],
        "diagnostics": {
            "changed_files_count": 1,
            "added_files_count": 1,
            "removed_files_count": 0,
            "evidence_counts_by_state": {"a": 1, "b": 1},
            "prioritized_files": [
                {"path": "README.md", "change_type": "changed", "priority_score": 9.4}
            ],
        },
        "state_a_citations": ["README.md:10-20"],
        "state_b_citations": ["CHANGELOG.md:1-12"],
        "state_a_evidence": [{"citation": "README.md:10-20"}],
        "state_b_evidence": [{"citation": "CHANGELOG.md:1-12"}],
    }

    monkeypatch.setattr(review_report, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(
        review_report,
        "compare_repo_states",
        lambda **kwargs: compare_result,
    )

    result = review_report.export_review_report(
        repo_url_a="https://github.com/example/repo",
        repo_url_b="https://github.com/example/repo",
        ref_a="v0.5.0",
        ref_b="v0.6.0",
        query="What changed from v0.5.0 to v0.6.0?",
        mode="release_diff",
    )

    markdown_path = Path(result["markdown_path"])
    json_path = Path(result["json_path"])

    assert result["mode"] == "release_diff"
    assert markdown_path.exists()
    assert json_path.exists()
    assert "Repo Review Report" in markdown_path.read_text(encoding="utf-8")
    assert "State A" in markdown_path.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"] == compare_result["answer"]
