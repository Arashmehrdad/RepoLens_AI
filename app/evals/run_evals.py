"""Run structured evaluation cases and persist versioned result reports."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.evals.eval_dataset import EVAL_CASES
from app.generation.answer_service import REFUSAL_TEXT, answer_question

DEFAULT_EVAL_VERSION = os.getenv("REPOLENS_EVAL_VERSION", "v0.5.0")
RESULTS_ROOT = Path("data/evals/results")
CONFIDENCE_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def citation_hit(citations: list[str], expected_paths: list[str]) -> bool:
    """Return True when every expected path appears in the citations list."""
    return all(
        any(expected_path in citation for citation in citations)
        for expected_path in expected_paths
    )


def confidence_meets_expectation(result_confidence: str, case: dict) -> bool:
    """Return True when a result confidence meets the case expectation."""
    actual_value = CONFIDENCE_ORDER.get(result_confidence, 0)

    if case.get("expected_confidence"):
        return result_confidence == case["expected_confidence"]

    minimum_confidence = case.get("minimum_confidence")
    if minimum_confidence:
        return actual_value >= CONFIDENCE_ORDER.get(minimum_confidence, 0)

    return True


def compute_relevance_proxy(case_result: dict) -> float:
    """Return a compact relevance score from deterministic eval signals."""
    components = [
        1.0 if case_result["refusal_ok"] else 0.0,
        1.0 if case_result["citation_ok"] else 0.0,
        1.0 if case_result["confidence_ok"] else 0.0,
    ]

    if not case_result["should_refuse"] and case_result.get("citations"):
        components.append(1.0)

    return round(sum(components) / len(components), 3)


def compute_latency_stats(latencies: list[float]) -> dict:
    """Return aggregate latency statistics for a set of eval cases."""
    if not latencies:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p95_ms": 0.0,
        }

    sorted_latencies = sorted(latencies)
    percentile_index = max(0, int(round(0.95 * len(sorted_latencies))) - 1)
    return {
        "count": len(sorted_latencies),
        "avg_ms": round(mean(sorted_latencies), 2),
        "min_ms": round(sorted_latencies[0], 2),
        "max_ms": round(sorted_latencies[-1], 2),
        "p95_ms": round(sorted_latencies[percentile_index], 2),
    }


def _build_group_summary(case_results: list[dict], group_key: str) -> dict:
    """Build grouped pass/failure summaries for a given case field."""
    grouped_results = defaultdict(list)

    for case_result in case_results:
        grouped_results[case_result[group_key]].append(case_result)

    summary = {}
    for key, results in grouped_results.items():
        latencies = [
            result["latency_ms"]
            for result in results
            if result.get("latency_ms") is not None
        ]
        summary[key] = {
            "total": len(results),
            "passed": sum(1 for result in results if result["passed"]),
            "pass_rate": round(
                sum(1 for result in results if result["passed"]) / len(results),
                3,
            ),
            "refusal_correctness": round(
                sum(1 for result in results if result["refusal_ok"]) / len(results),
                3,
            ),
            "citation_correctness": round(
                sum(1 for result in results if result["citation_ok"]) / len(results),
                3,
            ),
            "relevance_proxy_score": round(
                mean(result["relevance_proxy_score"] for result in results),
                3,
            ),
            "latency": compute_latency_stats(latencies),
        }

    return dict(summary)


def _build_output_dir(version: str, timestamp: str) -> Path:
    """Return the versioned eval output directory."""
    return RESULTS_ROOT / version / timestamp


def _build_markdown_report(summary: dict, case_results: list[dict]) -> str:
    """Build a compact markdown evaluation report."""
    lines = [
        f"# RepoLens AI Evaluation Report ({summary['version']})",
        "",
        f"- Timestamp: `{summary['timestamp']}`",
        f"- Total cases: `{summary['total_cases']}`",
        f"- Passed cases: `{summary['passed_cases']}`",
        f"- Pass rate: `{summary['pass_rate']}`",
        f"- Refusal correctness: `{summary['refusal_correctness']}`",
        f"- Citation correctness: `{summary['citation_correctness']}`",
        f"- Relevance proxy score: `{summary['relevance_proxy_score']}`",
        f"- Avg latency: `{summary['latency']['avg_ms']} ms`",
        "",
        "## Per Mode",
        "",
    ]

    for mode, mode_summary in summary["per_mode"].items():
        lines.append(
            f"- `{mode}`: pass `{mode_summary['passed']}/{mode_summary['total']}` "
            f"({mode_summary['pass_rate']})"
        )

    lines.extend(["", "## Per Category", ""])
    for category, category_summary in summary["per_category"].items():
        lines.append(
            f"- `{category}`: pass `{category_summary['passed']}/{category_summary['total']}` "
            f"({category_summary['pass_rate']})"
        )

    failing_cases = [case for case in case_results if not case["passed"]]
    lines.extend(["", "## Failures", ""])
    if not failing_cases:
        lines.append("- None")
    else:
        for case in failing_cases:
            lines.append(
                f"- `{case['name']}` ({case['mode']}/{case['category']}): "
                f"{case.get('error') or case.get('failure_reason', 'failed')}"
            )

    return "\n".join(lines) + "\n"


def _build_eval_error_result(case: dict, started_at: float, exc: Exception) -> dict:
    """Build a case result when the evaluation call crashes."""
    return {
        "name": case["name"],
        "category": case["category"],
        "query": case["query"],
        "mode": case["mode"],
        "should_refuse": case["should_refuse"],
        "expected_citations": case["expected_citations"],
        "latency_ms": round((perf_counter() - started_at) * 1000, 2),
        "answer": "",
        "citations": [],
        "confidence": "low",
        "outcome": "error",
        "refusal_ok": False,
        "citation_ok": False,
        "confidence_ok": False,
        "relevance_proxy_score": 0.0,
        "passed": False,
        "error": str(exc),
    }


def _build_eval_case_result(case: dict, result: dict, started_at: float) -> dict:
    """Build a normalized evaluation result for one answer."""
    refused = (
        result.get("outcome") == "refused"
        or result["answer"].strip() == REFUSAL_TEXT
    )
    refusal_ok = refused == case["should_refuse"]
    citation_ok = citation_hit(result["citations"], case["expected_citations"])
    confidence_ok = confidence_meets_expectation(result["confidence"], case)
    latency_ms = result.get("trace_summary", {}).get("request_latency_ms")
    if latency_ms is None:
        latency_ms = round((perf_counter() - started_at) * 1000, 2)

    case_result = {
        "name": case["name"],
        "category": case["category"],
        "query": case["query"],
        "mode": case["mode"],
        "notes": case.get("notes"),
        "should_refuse": case["should_refuse"],
        "expected_citations": case["expected_citations"],
        "answer": result["answer"],
        "citations": result["citations"],
        "confidence": result["confidence"],
        "outcome": result.get("outcome", "answered"),
        "latency_ms": latency_ms,
        "refusal_ok": refusal_ok,
        "citation_ok": citation_ok,
        "confidence_ok": confidence_ok,
        "error_code": result.get("error_code"),
        "error_message": result.get("error_message"),
        "trace_summary": result.get("trace_summary"),
        "retrieval_diagnostics": result.get("retrieval_diagnostics"),
    }
    case_result["relevance_proxy_score"] = compute_relevance_proxy(case_result)
    case_result["passed"] = refusal_ok and citation_ok and confidence_ok
    if not case_result["passed"]:
        case_result["failure_reason"] = (
            case_result.get("error_message")
            or "refusal/citation/confidence mismatch"
        )
    return case_result


def _evaluate_case(case: dict) -> dict:
    """Run one evaluation case and return a normalized result payload."""
    started_at = perf_counter()
    try:
        result = answer_question(
            query=case["query"],
            collection_name=case["collection_name"],
            mode=case["mode"],
        )
    except Exception as exc:  # pylint: disable=broad-except
        case_result = _build_eval_error_result(case, started_at, exc)
        print(f"\nCASE: {case['name']}")
        print("ERROR:", exc)
        return case_result

    case_result = _build_eval_case_result(case, result, started_at)
    print(f"\nCASE: {case['name']}")
    print("Outcome:", case_result["outcome"])
    print("Confidence:", case_result["confidence"])
    print("Citations:", case_result["citations"])
    print("PASS:", case_result["passed"])
    return case_result


def _build_summary(version: str, timestamp: str, case_results: list[dict]) -> dict:
    """Build comparable aggregate metrics for one eval run."""
    latencies = [
        case["latency_ms"]
        for case in case_results
        if case.get("latency_ms") is not None
    ]
    passed_cases = sum(1 for case in case_results if case["passed"])

    if not case_results:
        return {
            "version": version,
            "timestamp": timestamp,
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "refusal_correctness": 0.0,
            "citation_correctness": 0.0,
            "relevance_proxy_score": 0.0,
            "latency": compute_latency_stats([]),
            "per_mode": {},
            "per_category": {},
            "failures": [],
        }

    return {
        "version": version,
        "timestamp": timestamp,
        "total_cases": len(case_results),
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / len(case_results), 3),
        "refusal_correctness": round(
            sum(1 for case in case_results if case["refusal_ok"]) / len(case_results),
            3,
        ),
        "citation_correctness": round(
            sum(1 for case in case_results if case["citation_ok"]) / len(case_results),
            3,
        ),
        "relevance_proxy_score": round(
            mean(case["relevance_proxy_score"] for case in case_results),
            3,
        ),
        "latency": compute_latency_stats(latencies),
        "per_mode": _build_group_summary(case_results, "mode"),
        "per_category": _build_group_summary(case_results, "category"),
        "failures": [
            {
                "name": case["name"],
                "category": case["category"],
                "mode": case["mode"],
                "error_code": case.get("error_code"),
                "error_message": case.get("error_message") or case.get("error"),
                "failure_reason": case.get("failure_reason"),
            }
            for case in case_results
            if not case["passed"]
        ],
    }


def run_evals(version: str = DEFAULT_EVAL_VERSION) -> dict:
    """Run evaluation cases and save versioned results to disk."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = _build_output_dir(version, timestamp)
    case_results = [_evaluate_case(case) for case in EVAL_CASES]
    summary = _build_summary(version, timestamp, case_results)
    report_md = _build_markdown_report(summary, case_results)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (output_dir / "cases.json").write_text(
        json.dumps(case_results, indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(report_md, encoding="utf-8")

    print(f"\nPassed {summary['passed_cases']} / {len(case_results)} cases")
    print(f"Saved results to {output_dir}")
    return {
        "summary": summary,
        "cases": case_results,
        "output_dir": str(output_dir),
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the eval runner."""
    parser = argparse.ArgumentParser(description="Run RepoLens AI eval cases.")
    parser.add_argument(
        "--version",
        default=DEFAULT_EVAL_VERSION,
        help="Version label for saved eval results.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run_evals(version=arguments.version)
