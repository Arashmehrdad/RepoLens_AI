from app.core.tracing import log_trace
from app.generation.citations import format_citations
from app.generation.llm_writer import write_grounded_answer
from app.guardrails.evidence_gate import has_enough_evidence
from app.retrieval.postprocess import clean_retrieved_chunks
from app.retrieval.retriever import retrieve_chunks


def answer_question(
    query: str,
    collection_name: str = "repo_chunks",
    mode: str = "onboarding",
    n_results: int = 5,
) -> dict:
    retrieved_chunks = retrieve_chunks(
        query=query,
        collection_name=collection_name,
        n_results=n_results,
    )

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)

    if not has_enough_evidence(cleaned_chunks):
        result = {
            "answer": "I do not have enough evidence in the repository to answer that confidently.",
            "citations": [],
            "confidence": "low",
            "retrieved_chunks": cleaned_chunks,
        }

        log_trace(
            {
                "query": query,
                "mode": mode,
                "collection_name": collection_name,
                "confidence": result["confidence"],
                "citations": result["citations"],
                "answer": result["answer"],
            }
        )

        return result

    answer_text = write_grounded_answer(
        query=query,
        retrieved_chunks=cleaned_chunks,
        mode=mode,
    )

    result = {
        "answer": answer_text,
        "citations": format_citations(cleaned_chunks),
        "confidence": "high",
        "retrieved_chunks": cleaned_chunks,
    }

    log_trace(
        {
            "query": query,
            "mode": mode,
            "collection_name": collection_name,
            "confidence": result["confidence"],
            "citations": result["citations"],
            "answer": result["answer"],
        }
    )

    return result