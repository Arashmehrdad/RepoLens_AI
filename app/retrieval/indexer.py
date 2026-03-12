"""Vector indexing helpers."""

from app.retrieval.vector_store import get_vector_collection


def index_chunks(chunks: list[dict], collection_name: str = "repo_chunks") -> int:
    """Upsert chunk content plus rich metadata into the vector store."""
    collection = get_vector_collection(collection_name)

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{chunk['path']}::chunk_{chunk['chunk_index']}"
        ids.append(chunk_id)
        documents.append(chunk["content"])
        metadatas.append(
            {
                "path": chunk["path"],
                "path_lower": chunk["path_lower"],
                "filename": chunk["filename"],
                "filename_lower": chunk["filename_lower"],
                "suffix": chunk["suffix"],
                "stem": chunk["stem"],
                "parent_dirs_joined": chunk["parent_dirs_joined"],
                "depth": chunk["depth"],
                "chunk_index": chunk["chunk_index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "section": chunk["section"],
                "symbol": chunk["symbol"],
                "is_readme": chunk["is_readme"],
                "is_config": chunk["is_config"],
                "is_docker": chunk["is_docker"],
                "is_compose": chunk["is_compose"],
                "is_api": chunk["is_api"],
                "is_app_entry": chunk["is_app_entry"],
                "is_training": chunk["is_training"],
                "is_workflow": chunk["is_workflow"],
                "is_dependency_file": chunk["is_dependency_file"],
                "is_changelog": chunk["is_changelog"],
                "is_release_note": chunk["is_release_note"],
                "is_version_file": chunk["is_version_file"],
                "is_deployment_file": chunk["is_deployment_file"],
                "is_docs_update": chunk["is_docs_update"],
                "is_architecture_doc": chunk["is_architecture_doc"],
                "is_test_file": chunk["is_test_file"],
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return len(ids)
