"""End-to-end grounded answer generation service."""

from time import perf_counter
from uuid import uuid4

from app.core.tracing import log_trace
from app.core.tracing import build_trace_summary
from app.generation.citations import format_citations, select_citation_chunks
from app.generation.llm_writer import write_grounded_answer
from app.guardrails.evidence_gate import has_enough_evidence
from app.retrieval.postprocess import clean_retrieved_chunks
from app.retrieval.retriever import retrieve_chunks

REFUSAL_TEXT = "I do not have enough evidence in the repository to answer that confidently."
UNAVAILABLE_TEXT = (
    "Question answering requires a ready vector index and an embedding model "
    "available locally or via an initial network download."
)


class AnswerServiceUnavailableError(RuntimeError):
    """Raised when retrieval dependencies are unavailable for a question."""


def _build_refusal_result(retrieved_chunks: list[dict]) -> dict:
    """Return the standard refusal payload."""
    return {
        "answer": REFUSAL_TEXT,
        "citations": [],
        "confidence": "low",
        "retrieved_chunks": retrieved_chunks,
    }


def _top_paths(retrieved_chunks: list[dict], max_paths: int = 3) -> list[str]:
    """Return up to three unique top-ranked file paths."""
    top_paths = []
    seen_paths = set()

    for item in retrieved_chunks:
        path = item.get("metadata", {}).get("path")
        if not path or path in seen_paths:
            continue

        seen_paths.add(path)
        top_paths.append(path)

        if len(top_paths) >= max_paths:
            break

    return top_paths


def _build_trace_payload(
    trace_context: dict,
    result: dict,
    retrieved_chunks: list[dict],
    cleaned_chunks: list[dict],
    retrieval_diagnostics: dict,
) -> dict:
    """Build the structured trace payload written to disk."""
    return {
        **trace_context,
        "outcome": "answered" if result["confidence"] == "high" else "refused",
        "confidence": result["confidence"],
        "citations": result["citations"],
        "answer": result["answer"],
        "chunks_retrieved_count": len(retrieved_chunks),
        "chunks_after_cleaning_count": len(cleaned_chunks),
        "citations_count": len(result["citations"]),
        "top_paths": _top_paths(cleaned_chunks),
        "top_citations": result["citations"][:3],
        "retrieval_diagnostics": retrieval_diagnostics,
    }


def _finalize_result(
    result: dict,
    trace_context: dict,
    trace_state: dict,
) -> dict:
    """Attach trace information to a result payload."""
    trace_payload = _build_trace_payload(
        trace_context={
            **trace_context,
            "request_latency_ms": round(
                (perf_counter() - trace_state["request_started_at"]) * 1000,
                2,
            ),
            "retrieval_latency_ms": trace_state["retrieval_latency_ms"],
        },
        result=result,
        retrieved_chunks=trace_state["retrieved_chunks"],
        cleaned_chunks=trace_state["cleaned_chunks"],
        retrieval_diagnostics=trace_state["retrieval_diagnostics"],
    )
    trace_record = log_trace(trace_payload)
    result["trace_summary"] = build_trace_summary(trace_record)
    return result


def answer_question(
    query: str,
    collection_name: str = "repo_chunks",
    mode: str = "onboarding",
    n_results: int = 5,
) -> dict:
    """Retrieve evidence, apply guardrails, and return an answer payload."""
    request_started_at = perf_counter()
    trace_context = {
        "request_id": uuid4().hex,
        "query": query,
        "mode": mode,
        "collection_name": collection_name,
    }
    retrieval_started_at = perf_counter()
    try:
        retrieved_chunks, retrieval_diagnostics = retrieve_chunks(
            query=query,
            collection_name=collection_name,
            n_results=n_results,
            mode=mode,
            return_diagnostics=True,
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise AnswerServiceUnavailableError(UNAVAILABLE_TEXT) from exc
    retrieval_latency_ms = round((perf_counter() - retrieval_started_at) * 1000, 2)

    cleaned_chunks = clean_retrieved_chunks(
        retrieved_chunks,
        query_intents=set(retrieval_diagnostics.get("matched_intents", [])),
    )
    citation_chunks = select_citation_chunks(cleaned_chunks)
    trace_state = {
        "request_started_at": request_started_at,
        "retrieval_latency_ms": retrieval_latency_ms,
        "retrieved_chunks": retrieved_chunks,
        "cleaned_chunks": cleaned_chunks,
        "retrieval_diagnostics": retrieval_diagnostics,
    }

    if not has_enough_evidence(citation_chunks):
        result = _build_refusal_result(cleaned_chunks)
        return _finalize_result(
            result=result,
            trace_context=trace_context,
            trace_state=trace_state,
        )

    result = {
        "answer": write_grounded_answer(
            query=query,
            retrieved_chunks=citation_chunks,
            mode=mode,
        ),
        "citations": format_citations(citation_chunks),
        "confidence": "high",
        "retrieved_chunks": citation_chunks,
    }
    return _finalize_result(
        result=result,
        trace_context=trace_context,
        trace_state=trace_state,
    )
