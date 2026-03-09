from app.generation.citations import format_citations
from app.retrieval.retriever import retrieve_chunks


if __name__ == "__main__":
    query = "How do I run the Flask development server?"
    results = retrieve_chunks(query, n_results=5)
    citations = format_citations(results)

    print("Citations:")
    for citation in citations:
        print(citation)