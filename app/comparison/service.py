"""Grounded repo-state comparison and release-diff helpers."""

# pylint: disable=duplicate-code

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from app.core.errors import ComparisonError, RepoStateError, VectorStoreError
from app.generation.citations import format_line_citation, has_line_citation_metadata
from app.ingestion.manifest import get_manifest_files, load_manifest_for_state
from app.ingestion.pipeline import ingest_repository_state
from app.ingestion.state import RepoState, build_repo_state
from app.retrieval.retriever import classify_query_intents
from app.retrieval.vector_store import get_chunks_by_ids


IMPORTANT_FLAGS = (
    "is_readme",
    "is_changelog",
    "is_release_note",
    "is_version_file",
    "is_package_config",
    "is_dependency_file",
    "is_deployment_file",
    "is_docker",
    "is_compose",
    "is_workflow",
    "is_ci_file",
    "is_config",
    "is_app_entry",
    "is_api",
)
IMPACT_GROUPS = {
    "setup_impact": {
        "flags": {
            "is_readme",
            "is_config",
            "is_dependency_file",
            "is_package_config",
            "is_tutorial_doc",
            "is_app_entry",
        },
        "terms": ("setup", "install", "requirements", "pyproject", "env", "run"),
    },
    "deployment_impact": {
        "flags": {
            "is_deployment_file",
            "is_docker",
            "is_compose",
            "is_workflow",
            "is_ci_file",
        },
        "terms": ("deploy", "docker", "compose", "helm", "terraform", "vercel"),
    },
    "ci_cd_impact": {
        "flags": {"is_workflow", "is_ci_file"},
        "terms": ("workflow", "ci", "cd", ".github/workflows"),
    },
    "package_impact": {
        "flags": {
            "is_package_config",
            "is_version_file",
            "is_dependency_file",
        },
        "terms": ("version", "package", "requirements", "lock", "pyproject"),
    },
    "api_runtime_impact": {
        "flags": {"is_api", "is_app_entry", "is_config"},
        "terms": ("api", "main", "server", "schema", "runtime"),
    },
}
MODE_DEFAULT_QUERIES = {
    "compare": "What changed between these repository states?",
    "release_diff": "What changed between these releases?",
}


def _entry_flags(entry: dict | None) -> dict:
    """Return the stored manifest flags for one file entry."""
    return (entry or {}).get("flags", {})


def _combined_flags(entry_a: dict | None, entry_b: dict | None) -> set[str]:
    """Return the union of true manifest flags across two file entries."""
    flags = set()

    for source in (entry_a, entry_b):
        for name, value in _entry_flags(source).items():
            if value:
                flags.add(name)

    return flags


def _path_terms(path: str) -> set[str]:
    """Return lowercase path tokens for lightweight compare scoring."""
    return set(token for token in re.split(r"[/._-]+", path.lower()) if token)


def _build_diff_records(files_a: dict, files_b: dict) -> list[dict]:
    """Build normalized diff records from two manifest file inventories."""
    all_paths = sorted(set(files_a) | set(files_b))
    diff_records = []

    for path in all_paths:
        entry_a = files_a.get(path)
        entry_b = files_b.get(path)
        if entry_a and entry_b:
            if entry_a["file_hash"] == entry_b["file_hash"]:
                continue
            change_type = "changed"
        elif entry_a:
            change_type = "removed"
        else:
            change_type = "added"

        diff_records.append(
            {
                "path": path,
                "change_type": change_type,
                "entry_a": entry_a,
                "entry_b": entry_b,
                "flags": sorted(_combined_flags(entry_a, entry_b)),
                "path_terms": sorted(_path_terms(path)),
            }
        )

    return diff_records


def _score_diff_record(record: dict, intents: set[str], mode: str) -> float:
    """Return a priority score for one changed file record."""
    flags = set(record["flags"])
    terms = set(record["path_terms"])
    score = 0.0

    if record["change_type"] == "changed":
        score += 1.5
    else:
        score += 1.0

    score += sum(1.0 for flag in IMPORTANT_FLAGS if flag in flags)
    if "release_diff" == mode:
        score += sum(
            1.2
            for flag in (
                "is_changelog",
                "is_release_note",
                "is_version_file",
                "is_package_config",
                "is_workflow",
                "is_ci_file",
                "is_deployment_file",
                "is_readme",
            )
            if flag in flags
        )

    if "setup" in intents and flags & IMPACT_GROUPS["setup_impact"]["flags"]:
        score += 2.2
    if "deployment" in intents and flags & IMPACT_GROUPS["deployment_impact"]["flags"]:
        score += 2.5
    if "release" in intents and flags & {
        "is_changelog",
        "is_release_note",
        "is_version_file",
        "is_package_config",
        "is_workflow",
        "is_deployment_file",
        "is_readme",
    }:
        score += 2.8
    if "api" in intents and flags & IMPACT_GROUPS["api_runtime_impact"]["flags"]:
        score += 2.0
    if "debug" in intents and {"is_config", "is_app_entry", "is_api"} & flags:
        score += 1.6

    if terms & {"dockerfile", "docker", "compose", "workflow", "release", "changelog"}:
        score += 1.0

    return score


def _prioritize_diff_records(
    diff_records: list[dict],
    intents: set[str],
    mode: str,
    limit: int = 12,
) -> list[dict]:
    """Return the highest-signal changed files for comparison output."""
    prioritized = []

    for record in diff_records:
        prioritized.append(
            {
                **record,
                "priority_score": round(_score_diff_record(record, intents, mode), 3),
            }
        )

    prioritized.sort(
        key=lambda item: (item["priority_score"], item["path"]),
        reverse=True,
    )
    return prioritized[:limit]


def _filter_impact_paths(records: list[dict], impact_key: str) -> list[str]:
    """Return changed file paths that affect one compare impact bucket."""
    impact = IMPACT_GROUPS[impact_key]
    paths = []

    for record in records:
        flags = set(record["flags"])
        path_lower = record["path"].lower()
        if flags & impact["flags"] or any(term in path_lower for term in impact["terms"]):
            paths.append(record["path"])

    return paths


def _build_state_evidence(state_label: str, state: RepoState, records: list[dict]) -> list[dict]:
    """Load top grounded evidence snippets from one repo state."""
    evidence = []

    for record in records:
        entry = record["entry_a"] if state_label == "a" else record["entry_b"]
        if not entry or not entry.get("chunk_ids"):
            continue

        try:
            chunks = get_chunks_by_ids(state.collection_name, entry["chunk_ids"][:1])
        except VectorStoreError as exc:
            raise ComparisonError(
                "Comparison evidence could not be loaded from the vector store.",
                error_code=exc.error_code,
                diagnostics={
                    "state": state_label,
                    "collection_name": state.collection_name,
                    **exc.diagnostics,
                },
            ) from exc

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            if not has_line_citation_metadata(metadata):
                continue

            evidence.append(
                {
                    "state": state_label,
                    "path": metadata["path"],
                    "citation": format_line_citation(metadata),
                    "change_type": record["change_type"],
                    "excerpt": " ".join(chunk.get("content", "").split())[:220],
                }
            )
            break

        if len(evidence) >= 3:
            break

    return evidence


def _build_compare_summary(
    query: str,
    intents: set[str],
    prioritized: list[dict],
    impacts: dict,
    diagnostics: dict,
) -> tuple[str, str]:
    """Build a deterministic grounded compare summary and confidence label."""
    if not prioritized:
        return (
            "I could not find strong grounded repository evidence for that comparison.",
            "low",
        )

    changed_count = diagnostics["changed_files_count"]
    added_count = diagnostics["added_files_count"]
    removed_count = diagnostics["removed_files_count"]
    top_files = ", ".join(record["path"] for record in prioritized[:3])
    lines = [
        (
            f"Compared state B against state A for '{query}'. "
            f"{changed_count} files changed, {added_count} were added, and "
            f"{removed_count} were removed."
        ),
        f"Highest-signal changes: {top_files}.",
    ]

    if "deployment" in intents and impacts["deployment_impact"]:
        lines.append(
            "Deployment impact: " + ", ".join(impacts["deployment_impact"][:4]) + "."
        )
    elif "setup" in intents and impacts["setup_impact"]:
        lines.append("Setup impact: " + ", ".join(impacts["setup_impact"][:4]) + ".")
    elif "api" in intents and impacts["api_runtime_impact"]:
        lines.append(
            "API/runtime impact: " + ", ".join(impacts["api_runtime_impact"][:4]) + "."
        )
    elif "release" in intents:
        release_paths = (
            impacts["package_impact"]
            + impacts["deployment_impact"]
            + impacts["ci_cd_impact"]
        )
        if release_paths:
            lines.append(
                "Release-diff impact: " + ", ".join(release_paths[:5]) + "."
            )

    confidence = "high" if diagnostics["evidence_counts_by_state"]["a"] and diagnostics[
        "evidence_counts_by_state"
    ]["b"] else "medium"
    return " ".join(lines), confidence


def _extract_ignored_files(ingestion_payload: dict) -> dict:
    """Return the discovery skip counters for one ingested repo state."""
    diagnostics = ingestion_payload.get("ingestion_diagnostics", {})
    discovery = diagnostics.get("discovery", {})
    return discovery.get("skipped_reasons", {})


def _extract_noisy_files(ignored_files: dict) -> dict:
    """Return only the skip counters that indicate noisy repository content."""
    noisy_keys = {
        "noisy_filename",
        "generated_asset",
        "unsupported_extension",
        "denylisted_extension",
        "ignored_directory",
        "max_file_size_exceeded",
    }
    return {
        key: value
        for key, value in ignored_files.items()
        if key in noisy_keys and value
    }


def _load_state_manifest(state_payload: dict) -> tuple[RepoState, dict]:
    """Convert an ingestion payload into a RepoState plus loaded manifest."""
    state = build_repo_state(
        repo_url=state_payload["state"]["repo_url"],
        ref=state_payload["state"]["ref"],
        repo_path=state_payload["repo_path"] and Path(state_payload["repo_path"]),
        commit_sha=state_payload["state"].get("commit_sha"),
    )
    manifest = load_manifest_for_state(state)
    if not manifest:
        raise RepoStateError(
            "The requested repo state is not fully indexed yet.",
            error_code="repo_state_missing_manifest",
            diagnostics={"state_id": state.state_id, "collection_name": state.collection_name},
        )
    return state, manifest


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def compare_repo_states(
    repo_url_a: str,
    repo_url_b: str,
    ref_a: str | None = None,
    ref_b: str | None = None,
    query: str | None = None,
    mode: str = "compare",
) -> dict:
    """Compare two repo states and return a grounded multi-repo summary."""
    query = query or MODE_DEFAULT_QUERIES.get(mode, MODE_DEFAULT_QUERIES["compare"])
    state_a_payload = ingest_repository_state(repo_url_a, ref=ref_a)
    state_b_payload = ingest_repository_state(repo_url_b, ref=ref_b)
    state_a, manifest_a = _load_state_manifest(state_a_payload)
    state_b, manifest_b = _load_state_manifest(state_b_payload)

    files_a = get_manifest_files(manifest_a)
    files_b = get_manifest_files(manifest_b)
    diff_records = _build_diff_records(files_a, files_b)
    intents = classify_query_intents(query, mode="release" if mode == "release_diff" else None)
    prioritized = _prioritize_diff_records(diff_records, intents, mode)
    impacts = {
        key: _filter_impact_paths(prioritized, key)
        for key in IMPACT_GROUPS
    }
    evidence_a = _build_state_evidence("a", state_a, prioritized)
    evidence_b = _build_state_evidence("b", state_b, prioritized)
    diagnostics = {
        "compare_mode": mode,
        "state_a": state_a.to_dict(),
        "state_b": state_b.to_dict(),
        "changed_files_count": sum(
            1 for record in diff_records if record["change_type"] == "changed"
        ),
        "added_files_count": sum(
            1 for record in diff_records if record["change_type"] == "added"
        ),
        "removed_files_count": sum(
            1 for record in diff_records if record["change_type"] == "removed"
        ),
        "prioritized_files": [
            {
                "path": record["path"],
                "change_type": record["change_type"],
                "priority_score": record["priority_score"],
                "flags": record["flags"],
            }
            for record in prioritized
        ],
        "evidence_counts_by_state": {
            "a": len(evidence_a),
            "b": len(evidence_b),
        },
        "release_diff_signals": dict(
            Counter(
                flag
                for record in prioritized
                for flag in record["flags"]
                if flag
            )
        ),
        "incremental_stats": {
            "state_a": state_a_payload.get("incremental_stats"),
            "state_b": state_b_payload.get("incremental_stats"),
        },
        "ignored_files": {
            "state_a": _extract_ignored_files(state_a_payload),
            "state_b": _extract_ignored_files(state_b_payload),
        },
        "noisy_files": {
            "state_a": _extract_noisy_files(_extract_ignored_files(state_a_payload)),
            "state_b": _extract_noisy_files(_extract_ignored_files(state_b_payload)),
        },
    }
    if not prioritized:
        diagnostics["retrieval_miss_reason"] = "no_meaningful_diff_files"
    if not evidence_a and not evidence_b:
        diagnostics["weak_citation_reason"] = "no_grounded_compare_evidence"

    summary, confidence = _build_compare_summary(
        query=query,
        intents=intents,
        prioritized=prioritized,
        impacts=impacts,
        diagnostics=diagnostics,
    )
    combined_citations = [
        f"A: {item['citation']}" for item in evidence_a
    ] + [f"B: {item['citation']}" for item in evidence_b]

    return {
        "answer": summary,
        "citations": combined_citations,
        "confidence": confidence,
        "outcome": "compared" if prioritized else "weak_compare",
        "state_a": state_a.to_dict(),
        "state_b": state_b.to_dict(),
        "changed_files": [
            record["path"] for record in diff_records if record["change_type"] == "changed"
        ],
        "added_files": [
            record["path"] for record in diff_records if record["change_type"] == "added"
        ],
        "removed_files": [
            record["path"] for record in diff_records if record["change_type"] == "removed"
        ],
        "setup_impact": impacts["setup_impact"],
        "deployment_impact": impacts["deployment_impact"],
        "ci_cd_impact": impacts["ci_cd_impact"],
        "package_impact": impacts["package_impact"],
        "api_runtime_impact": impacts["api_runtime_impact"],
        "diagnostics": diagnostics,
        "state_a_citations": [item["citation"] for item in evidence_a],
        "state_b_citations": [item["citation"] for item in evidence_b],
        "state_a_evidence": evidence_a,
        "state_b_evidence": evidence_b,
    }
