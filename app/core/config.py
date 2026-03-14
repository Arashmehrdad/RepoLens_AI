"""Application configuration constants."""

import os
from pathlib import Path


def _get_int_env(name: str, default: int) -> int:
    """Return an integer environment variable with a safe fallback."""
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_csv_env(name: str, default: tuple[str, ...]) -> set[str]:
    """Return a normalized set of comma-separated environment values."""
    raw_value = os.getenv(name)
    if not raw_value:
        return {item.lower() for item in default}

    return {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
MANIFESTS_DIR = DATA_DIR / "manifests"
REPORTS_DIR = DATA_DIR / "reports"
EVAL_RESULTS_DIR = DATA_DIR / "evals" / "results"
VECTOR_STORE_DIR = Path(
    os.getenv("REPOLENS_VECTOR_STORE_DIR", str(DATA_DIR / "vector_store"))
)
EMBEDDING_CACHE_DIR = Path(
    os.getenv("REPOLENS_EMBEDDING_CACHE_DIR", str(DATA_DIR / "model_cache"))
)
LOGS_DIR = BASE_DIR / "logs"

MAX_FILES = _get_int_env("REPOLENS_MAX_FILES", 600)
MAX_FILE_SIZE_BYTES = _get_int_env("REPOLENS_MAX_FILE_SIZE_BYTES", 350_000)
MAX_TOTAL_BYTES = _get_int_env("REPOLENS_MAX_TOTAL_BYTES", 12_000_000)
DEFAULT_CHUNK_SIZE = _get_int_env("REPOLENS_CHUNK_SIZE", 1200)
DEFAULT_CHUNK_OVERLAP = _get_int_env("REPOLENS_CHUNK_OVERLAP", 200)
MIN_CHUNK_CHARACTERS = _get_int_env("REPOLENS_MIN_CHUNK_CHARACTERS", 40)

SUPPORTED_EXTENSIONS = _get_csv_env(
    "REPOLENS_ALLOWLIST_EXTENSIONS",
    (
        ".py",
        ".md",
        ".yml",
        ".yaml",
        ".json",
        ".txt",
        ".toml",
        ".ini",
        ".cfg",
        ".env",
        ".sh",
        ".rst",
        ".tsx",
        ".ts",
        ".js",
        ".jsx",
        ".css",
        ".html",
    ),
)

DENYLIST_EXTENSIONS = _get_csv_env(
    "REPOLENS_DENYLIST_EXTENSIONS",
    (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".ico",
        ".svg",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".7z",
        ".rar",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".mov",
        ".avi",
        ".dll",
        ".so",
        ".dylib",
        ".exe",
        ".bin",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".parquet",
        ".feather",
        ".ipynb",
    ),
)

DENYLIST_DIRECTORIES = _get_csv_env(
    "REPOLENS_DENYLIST_DIRECTORIES",
    (
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
        ".cache",
        ".ipynb_checkpoints",
        "vendor",
        "third_party",
        "site-packages",
        "logs",
        "data/evals/results",
        "data/manifests",
        "data/repos",
        "data/reports",
        "data/vector_store",
        "data/model_cache",
    ),
)

ALWAYS_INCLUDED_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "makefile",
    "requirements.txt",
    "pyproject.toml",
    ".env.example",
    ".env",
}
