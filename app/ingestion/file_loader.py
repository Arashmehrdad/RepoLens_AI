"""Repository file discovery helpers."""

from collections import Counter
from pathlib import Path

from app.core.config import (
    ALWAYS_INCLUDED_FILENAMES,
    DENYLIST_DIRECTORIES,
    DENYLIST_EXTENSIONS,
    MAX_FILES,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_BYTES,
    SUPPORTED_EXTENSIONS,
)


NOISY_FILENAMES = {
    ".ds_store",
    "thumbs.db",
    "eval_results.json",
    "traces.jsonl",
}
NOISY_NAME_TOKENS = (
    ".min.",
    ".bundle.",
    ".chunk.",
)


def should_skip_path(file_path: Path, repo_path: Path) -> bool:
    """Return True when a file should be excluded from ingestion."""
    return classify_skip_reason(file_path, repo_path) is not None


def classify_skip_reason(file_path: Path, repo_path: Path) -> str | None:
    """Return the reason a file should be excluded, or None when it is usable."""
    try:
        relative_path = file_path.relative_to(repo_path)
    except ValueError:
        return "outside_repo"

    relative_parts = relative_path.parts
    lowered_parts = [part.lower() for part in relative_parts]

    for index, part in enumerate(lowered_parts[:-1]):
        joined_prefix = "/".join(lowered_parts[: index + 1])
        if part in DENYLIST_DIRECTORIES or joined_prefix in DENYLIST_DIRECTORIES:
            return "ignored_directory"

    filename_lower = file_path.name.lower()
    suffix_lower = file_path.suffix.lower()

    if filename_lower in NOISY_FILENAMES:
        return "noisy_filename"

    if any(token in filename_lower for token in NOISY_NAME_TOKENS):
        return "generated_asset"

    if suffix_lower in DENYLIST_EXTENSIONS:
        return "denylisted_extension"

    return None


def is_supported_file(file_path: Path) -> bool:
    """Return True when a file is suitable for repository ingestion."""
    filename_lower = file_path.name.lower()

    if filename_lower in ALWAYS_INCLUDED_FILENAMES:
        return True

    if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return True

    if filename_lower.startswith("dockerfile"):
        return True

    return False


def discover_files(repo_path: Path) -> dict:
    """Collect supported repository files plus deterministic skip diagnostics."""
    supported_files = []
    skipped = Counter()
    total_bytes = 0

    for file_path in sorted(repo_path.rglob("*")):
        if not file_path.is_file():
            continue

        skip_reason = classify_skip_reason(file_path, repo_path)
        if skip_reason is not None:
            skipped[skip_reason] += 1
            continue

        if not is_supported_file(file_path):
            skipped["unsupported_extension"] += 1
            continue

        try:
            file_size = file_path.stat().st_size
        except OSError:
            skipped["stat_error"] += 1
            continue

        if file_size > MAX_FILE_SIZE_BYTES:
            skipped["max_file_size_exceeded"] += 1
            continue

        if len(supported_files) >= MAX_FILES:
            skipped["max_files_exceeded"] += 1
            continue

        if total_bytes + file_size > MAX_TOTAL_BYTES:
            skipped["max_total_bytes_exceeded"] += 1
            continue

        supported_files.append(file_path)
        total_bytes += file_size

    return {
        "files": supported_files,
        "total_bytes": total_bytes,
        "skipped_reasons": dict(skipped),
    }


def list_supported_files(repo_path: Path) -> list[Path]:
    """Collect supported repository files in deterministic order."""
    return discover_files(repo_path)["files"]
