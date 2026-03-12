"""Repository file discovery helpers."""

from pathlib import Path

from app.core.config import ALWAYS_INCLUDED_FILENAMES, SUPPORTED_EXTENSIONS


SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    "data/vector_store",
}


def should_skip_path(file_path: Path, repo_path: Path) -> bool:
    """Return True when a file should be excluded from ingestion."""
    try:
        relative_parts = file_path.relative_to(repo_path).parts
    except ValueError:
        return True

    for part in relative_parts[:-1]:
        if part in SKIP_DIRS:
            return True

    return False


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


def list_supported_files(repo_path: Path) -> list[Path]:
    """Collect supported repository files in deterministic order."""
    supported_files = []

    for file_path in sorted(repo_path.rglob("*")):
        if not file_path.is_file():
            continue

        if should_skip_path(file_path, repo_path):
            continue

        if is_supported_file(file_path):
            supported_files.append(file_path)

    return supported_files
