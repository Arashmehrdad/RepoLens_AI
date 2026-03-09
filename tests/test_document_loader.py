from pathlib import Path

from app.ingestion.document_loader import load_documents
from app.ingestion.file_loader import list_supported_files


if __name__ == "__main__":
    repo_path = Path("data/repos/flask")
    file_paths = list_supported_files(repo_path)
    documents = load_documents(file_paths, repo_path)

    print(f"Documents loaded: {len(documents)}")
    print(documents[0])