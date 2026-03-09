from pathlib import Path

from app.ingestion.file_loader import list_supported_files


if __name__ == "__main__":
    repo_path = Path("data/repos/flask")
    files = list_supported_files(repo_path)

    print(f"Supported files found: {len(files)}")
    for file_path in files[:20]:
        print(file_path)