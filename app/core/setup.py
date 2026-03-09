from app.core.config import DATA_DIR, REPOS_DIR, VECTOR_STORE_DIR, LOGS_DIR


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)