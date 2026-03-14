"""Repository cloning helpers."""

import os
import shutil
import stat
from pathlib import Path

from app.core.config import REPOS_DIR
from app.core.errors import RepositoryCloneError

CLONE_DEPENDENCY_ERROR = "Repository cloning requires GitPython and a Git executable on PATH."
CLONE_URL_ERROR = "Could not clone the repository. Check that the URL exists and is accessible."
CLONE_AUTH_ERROR = "Could not clone the repository because authentication or permissions failed."
CLONE_NETWORK_ERROR = "Could not clone the repository because the network request failed."
CLONE_CLEANUP_ERROR = "Could not prepare the repository directory for cloning."
CLONE_REF_ERROR = "Could not check out the requested repository ref."


def _get_git_dependencies() -> tuple[type, type, type]:
    """Import GitPython lazily so app startup does not require Git."""
    try:
        from git import Repo  # pylint: disable=import-outside-toplevel
        from git.exc import GitCommandError  # pylint: disable=import-outside-toplevel
        from git.exc import GitCommandNotFound  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RepositoryCloneError(
            CLONE_DEPENDENCY_ERROR,
            error_code="clone_dependency_missing",
            diagnostics={"missing_dependency": "gitpython_or_git"},
        ) from exc

    return Repo, GitCommandError, GitCommandNotFound


def _remove_readonly_and_retry(func, path, exc_info):
    """Retry removing files after clearing a read-only attribute."""
    del exc_info
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _prepare_target_path(target_path: Path) -> None:
    """Remove an existing clone target so the repo can be recloned cleanly."""
    if not target_path.exists():
        return

    try:
        shutil.rmtree(target_path, onerror=_remove_readonly_and_retry)
    except OSError as exc:
        raise RepositoryCloneError(
            CLONE_CLEANUP_ERROR,
            error_code="clone_cleanup_failed",
            diagnostics={"target_path": str(target_path), "reason": str(exc)},
        ) from exc


def _map_clone_command_error(repo_url: str, exc: Exception) -> RepositoryCloneError:
    """Map a Git clone failure into a safe application error."""
    message = str(exc).lower()
    diagnostics = {
        "repo_url": repo_url,
        "git_error": str(exc),
    }

    if any(
        token in message
        for token in ("authentication", "permission denied", "access denied", "403")
    ):
        return RepositoryCloneError(
            CLONE_AUTH_ERROR,
            error_code="clone_auth_failed",
            diagnostics=diagnostics,
        )

    if any(
        token in message
        for token in ("repository not found", "not found", "does not exist", "404")
    ):
        return RepositoryCloneError(
            CLONE_URL_ERROR,
            error_code="clone_invalid_url",
            diagnostics=diagnostics,
        )

    if any(
        token in message
        for token in ("could not resolve host", "failed to connect", "timed out", "network")
    ):
        return RepositoryCloneError(
            CLONE_NETWORK_ERROR,
            error_code="clone_network_failed",
            diagnostics=diagnostics,
        )

    return RepositoryCloneError(
        CLONE_URL_ERROR,
        error_code="clone_failed",
        diagnostics=diagnostics,
    )


def _map_ref_checkout_error(
    repo_url: str,
    ref: str,
    exc: Exception,
) -> RepositoryCloneError:
    """Map a ref checkout failure into a safe application error."""
    return RepositoryCloneError(
        CLONE_REF_ERROR,
        error_code="clone_invalid_ref",
        diagnostics={
            "repo_url": repo_url,
            "ref": ref,
            "git_error": str(exc),
        },
    )


def clone_repo(
    repo_url: str,
    ref: str | None = None,
    target_dir_name: str | None = None,
) -> Path:
    """Clone a repository URL into the local repos directory."""
    repo_class, git_command_error, git_command_not_found = _get_git_dependencies()
    repo_name = target_dir_name or repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_path = REPOS_DIR / repo_name

    _prepare_target_path(target_path)

    try:
        repo = repo_class.clone_from(repo_url, target_path)
        if ref:
            repo.git.checkout(ref)
    except git_command_not_found as exc:
        raise RepositoryCloneError(
            CLONE_DEPENDENCY_ERROR,
            error_code="clone_dependency_missing",
            diagnostics={"repo_url": repo_url, "reason": "git_executable_missing"},
        ) from exc
    except git_command_error as exc:
        if ref and "checkout" in str(exc).lower():
            raise _map_ref_checkout_error(repo_url, ref, exc) from exc
        raise _map_clone_command_error(repo_url, exc) from exc

    return target_path


def get_repo_commit_sha(repo_path: Path) -> str | None:
    """Return the current commit SHA for a Git repo when available."""
    try:
        repo_class, _, _ = _get_git_dependencies()
        return repo_class(repo_path).head.commit.hexsha
    except Exception:  # pylint: disable=broad-except
        return None
