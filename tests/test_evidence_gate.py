from app.guardrails.evidence_gate import has_enough_evidence
from app.retrieval.retriever import retrieve_chunks


if __name__ == "__main__":
    query = "How do I run the Flask development server?"
    results = retrieve_chunks(query, n_results=5)

    print("Enough evidence:", has_enough_evidence(results))