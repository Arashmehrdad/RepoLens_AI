from app.retrieval.vector_store import get_vector_collection


def index_chunks(chunks: list[dict], collection_name: str = "repo_chunks") -> int:
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
                "filename": chunk["filename"],
                "suffix": chunk["suffix"],
                "chunk_index": chunk["chunk_index"],
            }
        )

    if ids:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    return len(ids)