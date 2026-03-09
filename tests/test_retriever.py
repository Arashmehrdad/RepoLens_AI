from app.retrieval.retriever import retrieve_chunks


if __name__ == "__main__":
    query = "How do I run the Flask development server?"
    results = retrieve_chunks(query, n_results=5)

    print(f"Retrieved chunks: {len(results)}")
    for i, item in enumerate(results, start=1):
        print(f"\n--- Result {i} ---")
        print(item["metadata"])
        print(item["content"][:500])