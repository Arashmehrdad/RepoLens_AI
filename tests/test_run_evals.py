"""Tests for versioned evaluation result writing."""

from pathlib import Path

from app.evals import run_evals


def test_confidence_meets_expectation_supports_exact_and_minimum_thresholds():
    """Eval confidence checks should support exact and minimum expectations."""
    assert run_evals.confidence_meets_expectation("high", {"expected_confidence": "high"})
    assert not run_evals.confidence_meets_expectation("medium", {"expected_confidence": "high"})
    assert run_evals.confidence_meets_expectation("high", {"minimum_confidence": "medium"})
    assert not run_evals.confidence_meets_expectation("low", {"minimum_confidence": "medium"})


def test_run_evals_writes_versioned_summary_case_and_report_files(monkeypatch, tmp_path: Path):
    """Eval runs should write versioned result artifacts instead of overwriting one file."""
    fake_cases = [
        {
            "name": "setup_local_run",
            "category": "small_python_app",
            "collection_name": "repo_repolens_ai",
            "mode": "onboarding",
            "query": "How do I run this project locally?",
            "expected_citations": ["README.md"],
            "should_refuse": False,
            "expected_confidence": "high",
        }
    ]

    monkeypatch.setattr(run_evals, "EVAL_CASES", fake_cases)
    monkeypatch.setattr(run_evals, "RESULTS_ROOT", tmp_path / "eval-results")
    monkeypatch.setattr(
        run_evals,
        "answer_question",
        lambda query, collection_name, mode: {
            "answer": "Use uvicorn.",
            "citations": ["README.md:12-28"],
            "confidence": "high",
            "outcome": "answered",
            "error_code": None,
            "error_message": None,
            "trace_summary": {"request_latency_ms": 15.0},
            "retrieval_diagnostics": {"matched_intents": ["setup"]},
        },
    )

    result = run_evals.run_evals(version="v0.5.0")
    output_dir = Path(result["output_dir"])

    assert output_dir.parts[-2] == "v0.5.0"
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "cases.json").exists()
    assert (output_dir / "report.md").exists()
    assert result["summary"]["pass_rate"] == 1.0
