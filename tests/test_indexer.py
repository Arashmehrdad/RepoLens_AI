from pathlib import Path

from app.ingestion.document_loader import load_documents
from app.ingestion.file_loader import list_supported_files
from app.retrieval.chunker import chunk_documents
from app.retrieval.indexer import index_chunks


if __name__ == "__main__":
    repo_path = Path("data/repos/flask")
    file_paths = list_supported_files(repo_path)
    documents = load_documents(file_paths, repo_path)
    chunks = chunk_documents(documents)

    indexed_count = index_chunks(chunks)
    print(f"Indexed chunks: {indexed_count}")