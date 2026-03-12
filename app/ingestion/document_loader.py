"""Repository document loading helpers."""

from pathlib import Path


CONFIG_FILENAMES = {
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "pdm.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "environment.yml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    ".env.example",
    ".env",
    "makefile",
}


def _build_classification_flags(
    parts: tuple[str, ...],
    filename_lower: str,
    suffix: str,
    stem: str,
    path_lower: str,
) -> dict:
    """Classify a path into retrieval-friendly metadata flags."""
    config_suffixes = {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env", ".txt"}
    training_tokens = ["train", "trainer", "fit", "model", "pipeline"]
    dependency_filenames = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "package.json",
        "environment.yml",
    }

    return {
        "is_readme": filename_lower.startswith("readme"),
        "is_config": (
            filename_lower in CONFIG_FILENAMES
            or suffix in config_suffixes
            or "config" in filename_lower
            or "settings" in filename_lower
        ),
        "is_docker": filename_lower.startswith("dockerfile") or "docker" in path_lower,
        "is_compose": "compose" in filename_lower or "docker-compose" in path_lower,
        "is_api": any(part.lower() == "api" for part in parts) or "fastapi" in path_lower,
        "is_app_entry": stem in {"main", "app", "server", "run", "manage"},
        "is_training": any(token in path_lower for token in training_tokens),
        "is_workflow": ".github/workflows" in path_lower or "workflow" in path_lower,
        "is_dependency_file": filename_lower in dependency_filenames,
    }


def build_path_metadata(relative_path: Path) -> dict:
    """Build path-aware metadata used later for reranking."""
    parts = relative_path.parts
    filename = relative_path.name
    filename_lower = filename.lower()
    path_str = relative_path.as_posix()
    path_lower = path_str.lower()
    parent_parts = list(parts[:-1])
    joined_parents = "/".join(parent_parts).lower()
    stem = relative_path.stem.lower() if relative_path.suffix else filename_lower
    suffix = relative_path.suffix.lower()
    flags = _build_classification_flags(parts, filename_lower, suffix, stem, path_lower)

    return {
        "path": path_str,
        "path_lower": path_lower,
        "filename": filename,
        "filename_lower": filename_lower,
        "suffix": suffix,
        "stem": stem,
        "parent_dirs": parent_parts,
        "parent_dirs_joined": joined_parents,
        "depth": len(parts),
        **flags,
    }


def load_documents(file_paths: list[Path], repo_root: Path) -> list[dict]:
    """Load supported files and attach path-aware metadata."""
    documents = []

    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        relative_path = file_path.relative_to(repo_root)
        metadata = build_path_metadata(relative_path)

        documents.append(
            {
                "content": content,
                **metadata,
            }
        )

    return documents
