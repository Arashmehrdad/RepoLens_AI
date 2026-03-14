"""Regression aggregation helpers for versioned eval outputs."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from app.core.config import EVAL_RESULTS_DIR
from app.core.errors import RegressionError


METRIC_FIELDS = (
    "pass_rate",
    "relevance_proxy_score",
    "citation_correctness",
    "refusal_correctness",
)


def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file and return None when it does not exist."""
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegressionError(
            "An eval result file could not be loaded.",
            error_code="regression_load_failed",
            diagnostics={"path": str(path), "reason": str(exc)},
        ) from exc


def _coerce_float(value, default: float = 0.0) -> float:
    """Return a numeric metric value with a safe fallback."""
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_latency_summary(latency: dict | None) -> dict:
    """Return a backward-compatible latency summary."""
    latency = latency or {}
    return {
        "avg_ms": _coerce_float(latency.get("avg_ms")),
        "p95_ms": _coerce_float(latency.get("p95_ms")),
        "max_ms": _coerce_float(latency.get("max_ms")),
        "count": int(latency.get("count", 0) or 0),
    }


def _summarize_cases(cases: list[dict]) -> dict:
    """Build summary metrics when only case-level JSON is available."""
    if not cases:
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "refusal_correctness": 0.0,
            "citation_correctness": 0.0,
            "relevance_proxy_score": 0.0,
            "latency": _build_latency_summary({}),
        }

    latencies = [
        _coerce_float(case.get("latency_ms"), default=0.0)
        for case in cases
        if case.get("latency_ms") is not None
    ]
    return {
        "total_cases": len(cases),
        "passed_cases": sum(1 for case in cases if case.get("passed")),
        "pass_rate": round(
            sum(1 for case in cases if case.get("passed")) / len(cases),
            3,
        ),
        "refusal_correctness": round(
            sum(1 for case in cases if case.get("refusal_ok")) / len(cases),
            3,
        ),
        "citation_correctness": round(
            sum(1 for case in cases if case.get("citation_ok")) / len(cases),
            3,
        ),
        "relevance_proxy_score": round(
            mean(_coerce_float(case.get("relevance_proxy_score")) for case in cases),
            3,
        ),
        "latency": {
            "avg_ms": round(mean(latencies), 2) if latencies else 0.0,
            "p95_ms": max(latencies) if latencies else 0.0,
            "max_ms": max(latencies) if latencies else 0.0,
            "count": len(latencies),
        },
    }


def _normalize_run(version: str, timestamp: str, summary: dict, output_dir: Path) -> dict:
    """Return one normalized regression run record."""
    latency = _build_latency_summary(summary.get("latency"))
    return {
        "version": version,
        "timestamp": timestamp,
        "total_cases": int(summary.get("total_cases", 0) or 0),
        "passed_cases": int(summary.get("passed_cases", 0) or 0),
        "pass_rate": _coerce_float(summary.get("pass_rate")),
        "relevance_proxy_score": _coerce_float(summary.get("relevance_proxy_score")),
        "citation_correctness": _coerce_float(summary.get("citation_correctness")),
        "refusal_correctness": _coerce_float(summary.get("refusal_correctness")),
        "latency": latency,
        "path": str(output_dir),
    }


def load_regression_runs(results_root: Path = EVAL_RESULTS_DIR) -> list[dict]:
    """Load normalized regression runs from versioned eval result directories."""
    if not results_root.exists():
        return []

    runs = []

    for version_dir in sorted(path for path in results_root.iterdir() if path.is_dir()):
        for run_dir in sorted(path for path in version_dir.iterdir() if path.is_dir()):
            summary = _load_json(run_dir / "summary.json")
            cases = _load_json(run_dir / "cases.json")
            if not isinstance(summary, dict):
                summary = _summarize_cases(cases if isinstance(cases, list) else [])

            runs.append(
                _normalize_run(
                    version=version_dir.name,
                    timestamp=run_dir.name,
                    summary=summary,
                    output_dir=run_dir,
                )
            )

    return sorted(
        runs,
        key=lambda run: (run["version"], run["timestamp"]),
    )


def aggregate_regressions(
    versions: list[str] | None = None,
    results_root: Path = EVAL_RESULTS_DIR,
) -> dict:
    """Aggregate regression metrics across one or more eval versions."""
    runs = load_regression_runs(results_root=results_root)
    if versions:
        allowed_versions = set(versions)
        runs = [run for run in runs if run["version"] in allowed_versions]

    grouped_runs = defaultdict(list)
    for run in runs:
        grouped_runs[run["version"]].append(run)

    version_summaries = []
    metric_series = []
    for version, version_runs in sorted(grouped_runs.items()):
        latest_run = max(version_runs, key=lambda run: run["timestamp"])
        series = [
            {
                "timestamp": run["timestamp"],
                "pass_rate": run["pass_rate"],
                "relevance_proxy_score": run["relevance_proxy_score"],
                "citation_correctness": run["citation_correctness"],
                "refusal_correctness": run["refusal_correctness"],
                "latency_avg_ms": run["latency"]["avg_ms"],
            }
            for run in sorted(version_runs, key=lambda item: item["timestamp"])
        ]
        version_summaries.append(
            {
                "version": version,
                "run_count": len(version_runs),
                "latest_timestamp": latest_run["timestamp"],
                "latest_pass_rate": latest_run["pass_rate"],
                "latest_relevance_proxy_score": latest_run["relevance_proxy_score"],
                "latest_citation_correctness": latest_run["citation_correctness"],
                "latest_refusal_correctness": latest_run["refusal_correctness"],
                "latest_latency_avg_ms": latest_run["latency"]["avg_ms"],
                "avg_pass_rate": round(
                    mean(run["pass_rate"] for run in version_runs),
                    3,
                ),
                "avg_relevance_proxy_score": round(
                    mean(run["relevance_proxy_score"] for run in version_runs),
                    3,
                ),
                "avg_citation_correctness": round(
                    mean(run["citation_correctness"] for run in version_runs),
                    3,
                ),
                "avg_refusal_correctness": round(
                    mean(run["refusal_correctness"] for run in version_runs),
                    3,
                ),
                "avg_latency_ms": round(
                    mean(run["latency"]["avg_ms"] for run in version_runs),
                    2,
                ),
                "series": series,
            }
        )
        for point in series:
            metric_series.append({"version": version, **point})

    return {
        "selected_versions": sorted(grouped_runs),
        "versions": version_summaries,
        "runs": runs,
        "available_versions": sorted(grouped_runs),
        "metric_series": metric_series,
    }
