"""Filesystem setup helpers."""

from app.core.config import (
    DATA_DIR,
    EVAL_RESULTS_DIR,
    LOGS_DIR,
    MANIFESTS_DIR,
    REPORTS_DIR,
    REPOS_DIR,
    VECTOR_STORE_DIR,
)


def ensure_directories() -> None:
    """Create the directories the application expects to exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
