"""Repository cloning helpers."""

import shutil
from pathlib import Path

from app.core.config import REPOS_DIR

CLONE_DEPENDENCY_ERROR = "Repository cloning requires GitPython and a Git executable on PATH."


class RepositoryCloneError(RuntimeError):
    """Raised when repository cloning cannot be performed."""


def _get_git_dependencies() -> tuple[type, type]:
    """Import GitPython lazily so app startup does not require Git."""
    try:
        from git import Repo  # pylint: disable=import-outside-toplevel
        from git.exc import GitCommandNotFound  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RepositoryCloneError(CLONE_DEPENDENCY_ERROR) from exc

    return Repo, GitCommandNotFound


def clone_repo(repo_url: str) -> Path:
    """Clone a repository URL into the local repos directory."""
    repo_class, git_command_not_found = _get_git_dependencies()
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_path = REPOS_DIR / repo_name

    if target_path.exists():
        shutil.rmtree(target_path)

    try:
        repo_class.clone_from(repo_url, target_path)
    except git_command_not_found as exc:
        raise RepositoryCloneError(CLONE_DEPENDENCY_ERROR) from exc

    return target_path
