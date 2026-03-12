"""Application configuration constants."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
VECTOR_STORE_DIR = Path(
    os.getenv("REPOLENS_VECTOR_STORE_DIR", str(DATA_DIR / "vector_store"))
)
EMBEDDING_CACHE_DIR = Path(
    os.getenv("REPOLENS_EMBEDDING_CACHE_DIR", str(DATA_DIR / "model_cache"))
)
LOGS_DIR = BASE_DIR / "logs"

SUPPORTED_EXTENSIONS = {
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
}

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
