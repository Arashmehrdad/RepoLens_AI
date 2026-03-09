import shutil
from pathlib import Path

from git import Repo

from app.core.config import REPOS_DIR


def clone_repo(repo_url: str) -> Path:
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_path = REPOS_DIR / repo_name

    if target_path.exists():
        shutil.rmtree(target_path)

    Repo.clone_from(repo_url, target_path)
    return target_path
