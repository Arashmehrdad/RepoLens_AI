from app.retrieval.retriever import retrieve_chunks


def show_results(query: str) -> None:
    print(f"\nQUERY: {query}\n")

    results = retrieve_chunks(
        query=query,
        collection_name="repo_flask",
        n_results=5,
    )

    for i, item in enumerate(results, start=1):
        print(f"Result {i}")
        print("Path:", item["metadata"]["path"])
        print("Distance:", item["distance"])
        print("Preview:", item["content"][:200].replace("\n", " "))
        print("-" * 60)


if __name__ == "__main__":
    show_results("How do I run the Flask development server?")
    show_results("What is the capital of France?")