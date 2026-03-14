"""Exportable review-report helpers for compare and release-diff workflows."""

# pylint: disable=duplicate-code

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.comparison.service import compare_repo_states
from app.core.config import REPORTS_DIR
from app.core.errors import ReportGenerationError


def _build_report_id(compare_request: dict) -> str:
    """Return a deterministic report identifier for one compare request."""
    digest = hashlib.sha1(
        json.dumps(
            {
                "repo_url_a": compare_request["repo_url_a"],
                "repo_url_b": compare_request["repo_url_b"],
                "ref_a": compare_request.get("ref_a") or "default",
                "ref_b": compare_request.get("ref_b") or "default",
                "query": compare_request.get("query") or "",
                "mode": compare_request["mode"],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"{compare_request['mode']}_{digest}"


def _build_report_directory(state_a: dict, state_b: dict) -> Path:
    """Return the stable directory for reports comparing two repo states."""
    return REPORTS_DIR / f"{state_a['state_id']}__vs__{state_b['state_id']}"


def _build_report_payload(compare_result: dict, query: str | None, mode: str) -> dict:
    """Return the deterministic JSON structure used for exported reports."""
    diagnostics = compare_result.get("diagnostics", {})
    prioritized_files = diagnostics.get("prioritized_files", [])
    return {
        "mode": mode,
        "query": query,
        "outcome": compare_result.get("outcome"),
        "confidence": compare_result.get("confidence"),
        "summary": compare_result.get("answer"),
        "states": {
            "state_a": compare_result.get("state_a"),
            "state_b": compare_result.get("state_b"),
        },
        "changes": {
            "changed_files": compare_result.get("changed_files", []),
            "added_files": compare_result.get("added_files", []),
            "removed_files": compare_result.get("removed_files", []),
            "prioritized_files": prioritized_files,
        },
        "impacts": {
            "setup": compare_result.get("setup_impact", []),
            "deployment": compare_result.get("deployment_impact", []),
            "ci_cd": compare_result.get("ci_cd_impact", []),
            "package_versioning": compare_result.get("package_impact", []),
            "api_runtime": compare_result.get("api_runtime_impact", []),
        },
        "evidence": {
            "citations": compare_result.get("citations", []),
            "state_a_citations": compare_result.get("state_a_citations", []),
            "state_b_citations": compare_result.get("state_b_citations", []),
            "state_a_evidence": compare_result.get("state_a_evidence", []),
            "state_b_evidence": compare_result.get("state_b_evidence", []),
        },
        "diagnostics": diagnostics,
    }


def _build_markdown_report(report: dict) -> str:
    """Render a compact markdown review report."""
    state_a = report["states"]["state_a"]
    state_b = report["states"]["state_b"]
    changes = report["changes"]
    impacts = report["impacts"]
    evidence = report["evidence"]
    diagnostics = report["diagnostics"]
    lines = [
        f"# Repo Review Report ({report['mode']})",
        "",
        f"- Outcome: `{report['outcome']}`",
        f"- Confidence: `{report['confidence']}`",
        f"- Query: `{report['query'] or 'default compare summary'}`",
        "",
        "## Compared States",
        "",
        f"- State A: `{state_a['normalized_repo_url']}` @ `{state_a['ref']}`",
        f"- State B: `{state_b['normalized_repo_url']}` @ `{state_b['ref']}`",
        "",
        "## Summary",
        "",
        report["summary"] or "No grounded comparison summary was available.",
        "",
        "## Important Changes",
        "",
        f"- Changed files ({len(changes['changed_files'])}): "
        + (", ".join(changes["changed_files"][:8]) or "None"),
        f"- Added files ({len(changes['added_files'])}): "
        + (", ".join(changes["added_files"][:8]) or "None"),
        f"- Removed files ({len(changes['removed_files'])}): "
        + (", ".join(changes["removed_files"][:8]) or "None"),
        "",
        "## Impact Review",
        "",
        f"- Setup impact: {', '.join(impacts['setup'][:6]) or 'None'}",
        f"- Deployment impact: {', '.join(impacts['deployment'][:6]) or 'None'}",
        f"- CI/CD impact: {', '.join(impacts['ci_cd'][:6]) or 'None'}",
        f"- Package/versioning impact: {', '.join(impacts['package_versioning'][:6]) or 'None'}",
        f"- API/runtime impact: {', '.join(impacts['api_runtime'][:6]) or 'None'}",
        "",
        "## Evidence",
        "",
    ]

    if evidence["citations"]:
        for citation in evidence["citations"][:6]:
            lines.append(f"- `{citation}`")
    else:
        lines.append("- No grounded citations were available.")

    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            f"- Changed files count: `{diagnostics.get('changed_files_count', 0)}`",
            f"- Added files count: `{diagnostics.get('added_files_count', 0)}`",
            f"- Removed files count: `{diagnostics.get('removed_files_count', 0)}`",
            "- Evidence counts by state: "
            + json.dumps(diagnostics.get("evidence_counts_by_state", {}), sort_keys=True),
        ]
    )

    if diagnostics.get("weak_citation_reason"):
        lines.append(f"- Weak citation reason: `{diagnostics['weak_citation_reason']}`")
    if diagnostics.get("retrieval_miss_reason"):
        lines.append(f"- Retrieval miss reason: `{diagnostics['retrieval_miss_reason']}`")

    return "\n".join(lines) + "\n"


def export_review_report(**compare_request) -> dict:
    """Generate and persist a deterministic compare review report."""
    compare_result = compare_repo_states(
        repo_url_a=compare_request["repo_url_a"],
        repo_url_b=compare_request["repo_url_b"],
        ref_a=compare_request.get("ref_a"),
        ref_b=compare_request.get("ref_b"),
        query=compare_request.get("query"),
        mode=compare_request.get("mode", "compare"),
    )
    report = _build_report_payload(
        compare_result,
        query=compare_request.get("query"),
        mode=compare_request.get("mode", "compare"),
    )
    state_a = report["states"]["state_a"]
    state_b = report["states"]["state_b"]
    report_id = _build_report_id(compare_request)
    report_dir = _build_report_directory(state_a, state_b)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{report_id}.json"
    markdown_path = report_dir / f"{report_id}.md"
    markdown = _build_markdown_report(report)

    try:
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        raise ReportGenerationError(
            "The review report could not be written to disk.",
            error_code="report_write_failed",
            diagnostics={
                "report_id": report_id,
                "report_dir": str(report_dir),
                "reason": str(exc),
            },
        ) from exc

    return {
        "report_id": report_id,
        "mode": compare_request.get("mode", "compare"),
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "markdown": markdown,
        "report": report,
    }
