"""Tests for eval regression aggregation helpers."""

import json

from app.evals import regressions


def test_aggregate_regressions_handles_mixed_historical_run_formats(tmp_path):
    """Regression aggregation should tolerate missing fields and summary-only runs."""
    old_run = tmp_path / "v0.5.0" / "20260101T120000Z"
    new_run = tmp_path / "v0.6.0" / "20260313T120000Z"
    old_run.mkdir(parents=True)
    new_run.mkdir(parents=True)

    (old_run / "summary.json").write_text(
        json.dumps(
            {
                "total_cases": 2,
                "passed_cases": 1,
                "pass_rate": 0.5,
                "latency": {"avg_ms": 45.0, "count": 2},
            }
        ),
        encoding="utf-8",
    )
    (new_run / "cases.json").write_text(
        json.dumps(
            [
                {
                    "name": "case-a",
                    "passed": True,
                    "refusal_ok": True,
                    "citation_ok": True,
                    "relevance_proxy_score": 1.0,
                    "latency_ms": 20.0,
                },
                {
                    "name": "case-b",
                    "passed": False,
                    "refusal_ok": True,
                    "citation_ok": False,
                    "relevance_proxy_score": 0.5,
                    "latency_ms": 30.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = regressions.aggregate_regressions(results_root=tmp_path)

    assert result["available_versions"] == ["v0.5.0", "v0.6.0"]
    assert len(result["versions"]) == 2
    assert any(item["version"] == "v0.6.0" for item in result["metric_series"])
    assert result["versions"][0]["run_count"] == 1
    assert result["versions"][1]["latest_citation_correctness"] == 0.5


def test_aggregate_regressions_can_filter_selected_versions(tmp_path):
    """Regression aggregation should support comparing selected versions only."""
    for version in ("v0.5.0", "v0.6.0"):
        run_dir = tmp_path / version / "20260313T120000Z"
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(
            json.dumps({"total_cases": 1, "passed_cases": 1, "pass_rate": 1.0}),
            encoding="utf-8",
        )

    result = regressions.aggregate_regressions(
        versions=["v0.6.0"],
        results_root=tmp_path,
    )

    assert result["available_versions"] == ["v0.6.0"]
    assert all(item["version"] == "v0.6.0" for item in result["runs"])
