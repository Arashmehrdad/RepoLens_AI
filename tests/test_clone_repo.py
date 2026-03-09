from app.ingestion.repo_manager import clone_repo


if __name__ == "__main__":
    repo_path = clone_repo("https://github.com/pallets/flask.git")
    print(f"Cloned to: {repo_path}")