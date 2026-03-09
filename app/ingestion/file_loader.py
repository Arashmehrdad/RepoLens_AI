from pathlib import Path

from app.core.config import SUPPORTED_EXTENSIONS


def list_supported_files(repo_path: Path) -> list[Path]:
    supported_files = []

    for file_path in repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported_files.append(file_path)

    return supported_files