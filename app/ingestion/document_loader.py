"""Repository document loading helpers."""

from collections import Counter
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
CHANGELOG_TERMS = {"changelog", "history", "release-notes", "release_notes", "changes"}
RELEASE_NOTE_TERMS = {"release-note", "release-notes", "release_notes"}
VERSION_FILENAMES = {
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "poetry.lock",
    "pdm.lock",
    "version.txt",
}
DEPLOYMENT_TERMS = {
    "deploy",
    "deployment",
    "k8s",
    "kubernetes",
    "helm",
    "terraform",
    "infra",
    "nginx",
    "gunicorn",
    "render",
    "vercel",
    "fly.toml",
    "procfile",
}
ARCHITECTURE_TERMS = {"architecture", "design", "adr", "overview", "system"}
TEST_DIR_NAMES = {"tests", "test"}
EXAMPLE_DIR_NAMES = {"examples", "example", "samples", "sample", "demo"}
CI_TERMS = {"ci", ".circleci", "gitlab-ci", "azure-pipelines", "jenkins"}
PACKAGE_CONFIG_FILENAMES = {
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "pdm.lock",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
}
TUTORIAL_TERMS = {"tutorial", "guide", "getting-started", "quickstart", "walkthrough"}
CONFIG_SUFFIXES = {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env", ".txt"}
TRAINING_TOKENS = ["train", "trainer", "fit", "model", "pipeline"]
DEPENDENCY_FILENAMES = {
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "package.json",
    "environment.yml",
}
RELEASE_TERMS = CHANGELOG_TERMS | {"release"}


def _is_version_file(filename_lower: str, stem: str, path_lower: str) -> bool:
    """Return True when a file likely stores version information."""
    return (
        filename_lower in VERSION_FILENAMES
        or stem in {"version", "_version"}
        or "/version" in path_lower
    )


def _is_docs_update(is_readme: bool, suffix: str, path_lower: str) -> bool:
    """Return True when a path points to documentation content."""
    return is_readme or suffix == ".md" or path_lower.startswith("docs/") or "/docs/" in path_lower


def _is_test_file(parts: tuple[str, ...], filename_lower: str) -> bool:
    """Return True when a path is a test file or under a test directory."""
    return (
        filename_lower.startswith("test_")
        or filename_lower.endswith("_test.py")
        or any(part.lower() in TEST_DIR_NAMES for part in parts)
    )


def _is_deployment_file(path_lower: str, is_docker: bool, is_compose: bool) -> bool:
    """Return True when a file is part of deployment or hosting setup."""
    return is_docker or is_compose or any(term in path_lower for term in DEPLOYMENT_TERMS)


def _is_example_file(parts: tuple[str, ...], filename_lower: str, path_lower: str) -> bool:
    """Return True when a path points to example or sample code."""
    return (
        filename_lower.startswith("example")
        or any(part.lower() in EXAMPLE_DIR_NAMES for part in parts)
        or "/examples/" in path_lower
    )


def _is_ci_file(path_lower: str, is_workflow: bool) -> bool:
    """Return True when a file belongs to CI or release automation."""
    return is_workflow or any(term in path_lower for term in CI_TERMS)


def _is_release_note(
    parts: tuple[str, ...],
    filename_lower: str,
    path_lower: str,
    suffix: str,
) -> bool:
    """Return True when a path looks like dedicated release-note content."""
    return (
        suffix == ".md"
        and (
            any(term in path_lower for term in CHANGELOG_TERMS)
            or
            any(term in filename_lower for term in RELEASE_NOTE_TERMS)
            or any(term in path_lower for term in RELEASE_NOTE_TERMS)
            or any(part.lower() == "releases" for part in parts)
        )
    )


def _is_tutorial_doc(path_lower: str, suffix: str) -> bool:
    """Return True when a path looks like a getting-started or tutorial document."""
    return suffix in {".md", ".rst"} and any(term in path_lower for term in TUTORIAL_TERMS)


def _build_classification_flags(
    parts: tuple[str, ...],
    filename_lower: str,
    suffix: str,
    stem: str,
    path_lower: str,
) -> dict:
    """Classify a path into retrieval-friendly metadata flags."""
    is_readme = filename_lower.startswith("readme")
    is_docker = filename_lower.startswith("dockerfile") or "docker" in path_lower
    is_compose = "compose" in filename_lower or "docker-compose" in path_lower
    is_workflow = ".github/workflows" in path_lower

    return {
        "is_readme": is_readme,
        "is_config": (
            filename_lower in CONFIG_FILENAMES
            or suffix in CONFIG_SUFFIXES
            or "config" in filename_lower
            or "settings" in filename_lower
        ),
        "is_docker": is_docker,
        "is_compose": is_compose,
        "is_api": any(part.lower() == "api" for part in parts) or "fastapi" in path_lower,
        "is_app_entry": stem in {"main", "app", "server", "run", "manage"},
        "is_training": any(token in path_lower for token in TRAINING_TOKENS),
        "is_workflow": is_workflow,
        "is_dependency_file": filename_lower in DEPENDENCY_FILENAMES,
        "is_changelog": any(term in path_lower for term in CHANGELOG_TERMS),
        "is_release_note": _is_release_note(parts, filename_lower, path_lower, suffix),
        "is_version_file": _is_version_file(filename_lower, stem, path_lower),
        "is_deployment_file": _is_deployment_file(path_lower, is_docker, is_compose),
        "is_docs_update": _is_docs_update(is_readme, suffix, path_lower),
        "is_architecture_doc": any(term in path_lower for term in ARCHITECTURE_TERMS),
        "is_test_file": _is_test_file(parts, filename_lower),
        "is_example_file": _is_example_file(parts, filename_lower, path_lower),
        "is_ci_file": _is_ci_file(path_lower, is_workflow),
        "is_package_config": filename_lower in PACKAGE_CONFIG_FILENAMES,
        "is_tutorial_doc": _is_tutorial_doc(path_lower, suffix),
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


def load_documents_with_stats(file_paths: list[Path], repo_root: Path) -> dict:
    """Load supported files, attach metadata, and track skipped reasons."""
    documents = []
    skipped = Counter()

    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped["decode_error"] += 1
            continue
        except OSError:
            skipped["read_error"] += 1
            continue

        if not content.strip():
            skipped["empty_file"] += 1
            continue

        try:
            byte_size = file_path.stat().st_size
        except OSError:
            skipped["stat_error"] += 1
            continue

        relative_path = file_path.relative_to(repo_root)
        metadata = build_path_metadata(relative_path)
        metadata["byte_size"] = byte_size

        documents.append(
            {
                "content": content,
                **metadata,
            }
        )

    return {
        "documents": documents,
        "skipped_reasons": dict(skipped),
    }


def load_documents(file_paths: list[Path], repo_root: Path) -> list[dict]:
    """Load supported files and attach path-aware metadata."""
    return load_documents_with_stats(file_paths, repo_root)["documents"]
