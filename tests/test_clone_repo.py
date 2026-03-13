"""Tests for clone-related behavior and Git dependency isolation."""

import builtins
import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ingestion import repo_manager


def _clear_modules(*prefixes: str) -> None:
    """Remove cached modules so imports execute again inside a test."""
    for module_name in list(sys.modules):
        if any(
            module_name == prefix or module_name.startswith(f"{prefix}.")
            for prefix in prefixes
        ):
            sys.modules.pop(module_name, None)


def _block_git_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force `git` imports to fail so lazy import behavior can be tested."""
    real_import = builtins.__import__

    def guarded_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        if name == "git" or name.startswith("git."):
            raise ImportError("git unavailable for test")
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_app_api_main_import_does_not_require_git(monkeypatch: pytest.MonkeyPatch):
    """Importing the API module should not trigger a Git dependency."""
    _clear_modules("app.api.main", "app.ingestion.pipeline", "app.ingestion.repo_manager", "git")
    _block_git_imports(monkeypatch)

    module = importlib.import_module("app.api.main")

    assert module.app.title == "RepoLens AI"


def test_clone_repo_raises_clear_error_when_git_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Cloning should fail with an explicit application error when Git is missing."""
    _clear_modules("git")
    _block_git_imports(monkeypatch)
    monkeypatch.setattr(repo_manager, "REPOS_DIR", tmp_path)

    with pytest.raises(repo_manager.RepositoryCloneError, match=repo_manager.CLONE_DEPENDENCY_ERROR):
        repo_manager.clone_repo("https://github.com/pallets/flask.git")


def test_clone_repo_still_uses_gitpython_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Cloning should still delegate to GitPython when dependencies are available."""
    calls = []

    class FakeRepo:
        """Minimal fake GitPython Repo class."""

        @staticmethod
        def clone_from(repo_url: str, target_path: Path) -> None:
            calls.append((repo_url, Path(target_path)))
            Path(target_path).mkdir(parents=True, exist_ok=True)

    class FakeGitCommandNotFound(Exception):
        """Placeholder Git command error."""

    class FakeGitCommandError(Exception):
        """Placeholder Git command failure."""

    fake_git = types.ModuleType("git")
    fake_git.__path__ = []
    fake_git.Repo = FakeRepo

    fake_git_exc = types.ModuleType("git.exc")
    fake_git_exc.GitCommandError = FakeGitCommandError
    fake_git_exc.GitCommandNotFound = FakeGitCommandNotFound
    fake_git.exc = fake_git_exc

    monkeypatch.setitem(sys.modules, "git", fake_git)
    monkeypatch.setitem(sys.modules, "git.exc", fake_git_exc)
    monkeypatch.setattr(repo_manager, "REPOS_DIR", tmp_path)

    target_path = repo_manager.clone_repo("https://github.com/example/demo.git")

    assert target_path == tmp_path / "demo"
    assert calls == [("https://github.com/example/demo.git", target_path)]


def test_ingest_endpoint_returns_controlled_error(monkeypatch: pytest.MonkeyPatch):
    """The ingest endpoint should convert clone dependency failures into HTTP errors."""
    from app.api import main as api_main
    from app.ingestion import repo_manager as current_repo_manager

    def failing_ingest_repository(repo_url: str) -> dict:
        raise current_repo_manager.RepositoryCloneError(
            current_repo_manager.CLONE_DEPENDENCY_ERROR,
            error_code="clone_dependency_missing",
        )

    monkeypatch.setattr(api_main, "ingest_repository", failing_ingest_repository)

    with TestClient(api_main.app) as client:
        response = client.post("/ingest", json={"repo_url": "https://github.com/example/demo.git"})

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "clone_dependency_missing"
    assert response.json()["detail"]["error_message"] == current_repo_manager.CLONE_DEPENDENCY_ERROR


def test_clone_repo_maps_invalid_url_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Git command failures should be mapped to safe invalid-URL clone errors."""

    class FakeRepo:
        """Repo stub that raises a Git-style command error."""

        @staticmethod
        def clone_from(repo_url: str, target_path: Path) -> None:
            del repo_url, target_path
            raise FakeGitCommandError("fatal: repository not found")

    class FakeGitCommandError(Exception):
        """Placeholder Git command error."""

    class FakeGitCommandNotFound(Exception):
        """Placeholder Git command not found error."""

    monkeypatch.setattr(repo_manager, "_get_git_dependencies", lambda: (FakeRepo, FakeGitCommandError, FakeGitCommandNotFound))
    monkeypatch.setattr(repo_manager, "REPOS_DIR", tmp_path)

    with pytest.raises(repo_manager.RepositoryCloneError) as exc_info:
        repo_manager.clone_repo("https://github.com/example/missing.git")

    assert exc_info.value.error_code == "clone_invalid_url"
