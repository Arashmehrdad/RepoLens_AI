from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
LOGS_DIR = BASE_DIR / "logs"

SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
}