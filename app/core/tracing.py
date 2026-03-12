"""Trace logging utilities."""

import json
from datetime import datetime, UTC

from app.core.config import LOGS_DIR


TRACE_FILE = LOGS_DIR / "traces.jsonl"
TRACE_SUMMARY_FIELDS = (
    "timestamp",
    "request_id",
    "outcome",
    "confidence",
    "request_latency_ms",
    "retrieval_latency_ms",
    "chunks_retrieved_count",
    "chunks_after_cleaning_count",
    "citations_count",
    "top_paths",
    "top_citations",
)


def build_trace_entry(payload: dict) -> dict:
    """Build a structured trace event payload."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        **payload,
    }


def build_trace_summary(trace: dict) -> dict:
    """Build the compact trace summary returned to the API/UI."""
    retrieval_diagnostics = trace.get("retrieval_diagnostics", {})
    summary = {field: trace.get(field) for field in TRACE_SUMMARY_FIELDS}
    summary["query_intents"] = retrieval_diagnostics.get("matched_intents", [])
    summary["retrieval_fetch_count"] = retrieval_diagnostics.get("fetch_count")
    summary["raw_results_count"] = retrieval_diagnostics.get("raw_result_count")
    return summary


def log_trace(payload: dict) -> dict:
    """Append a structured trace event to the JSONL trace log."""
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    trace = build_trace_entry(payload)

    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")

    return trace
