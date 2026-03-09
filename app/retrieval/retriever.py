from app.retrieval.vector_store import get_vector_collection


def retrieve_chunks(
    query: str,
    collection_name: str = "repo_chunks",
    n_results: int = 5,
) -> list[dict]:
    collection = get_vector_collection(collection_name)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    retrieved_chunks = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    for index, document in enumerate(documents):
        retrieved_chunks.append(
            {
                "content": document,
                "metadata": metadatas[index],
                "distance": distances[index] if index < len(distances) else None,
            }
        )

    return retrieved_chunks