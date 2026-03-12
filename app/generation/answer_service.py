"""End-to-end grounded answer generation service."""

from app.core.tracing import log_trace
from app.generation.citations import format_citations, select_citation_chunks
from app.generation.llm_writer import write_grounded_answer
from app.guardrails.evidence_gate import has_enough_evidence
from app.retrieval.postprocess import clean_retrieved_chunks
from app.retrieval.retriever import retrieve_chunks

REFUSAL_TEXT = "I do not have enough evidence in the repository to answer that confidently."


def _build_refusal_result(retrieved_chunks: list[dict]) -> dict:
    """Return the standard refusal payload."""
    return {
        "answer": REFUSAL_TEXT,
        "citations": [],
        "confidence": "low",
        "retrieved_chunks": retrieved_chunks,
    }


def answer_question(
    query: str,
    collection_name: str = "repo_chunks",
    mode: str = "onboarding",
    n_results: int = 5,
) -> dict:
    """Retrieve evidence, apply guardrails, and return an answer payload."""
    retrieved_chunks = retrieve_chunks(
        query=query,
        collection_name=collection_name,
        n_results=n_results,
    )

    cleaned_chunks = clean_retrieved_chunks(retrieved_chunks)
    citation_chunks = select_citation_chunks(cleaned_chunks)

    if not has_enough_evidence(citation_chunks):
        result = _build_refusal_result(cleaned_chunks)

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
        retrieved_chunks=citation_chunks,
        mode=mode,
    )

    result = {
        "answer": answer_text,
        "citations": format_citations(citation_chunks),
        "confidence": "high",
        "retrieved_chunks": citation_chunks,
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
