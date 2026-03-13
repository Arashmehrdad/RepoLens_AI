"""End-to-end grounded answer generation service."""

import re
from time import perf_counter
from uuid import uuid4

from app.core.errors import LLMDependencyError, LLMInvocationError, RetrievalError
from app.core.tracing import build_trace_summary
from app.core.tracing import log_trace
from app.generation.citations import format_citations, select_citation_chunks
from app.generation.llm_writer import write_grounded_answer
from app.guardrails.evidence_gate import has_enough_evidence
from app.retrieval.postprocess import clean_retrieved_chunks
from app.retrieval.retriever import retrieve_chunks

REFUSAL_TEXT = "I do not have enough evidence in the repository to answer that confidently."
RETRIEVAL_FAILURE_TEXT = (
    "I could not safely retrieve grounded repository evidence for that question."
)
FALLBACK_PREFIX = (
    "I found relevant repository evidence, but the model summary was unavailable. "
    "Here are the strongest grounded excerpts:"
)


def _build_response(
    answer: str,
    citations: list[str],
    confidence: str,
    outcome: str,
    **extra_fields,
) -> dict:
    """Build the standard answer-service payload."""
    response = {
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "outcome": outcome,
        "error_code": None,
        "error_message": None,
        "retrieval_diagnostics": {},
        "retrieved_chunks": [],
    }
    response.update(extra_fields)
    return response


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
        "outcome": result["outcome"],
        "confidence": result["confidence"],
        "error_code": result.get("error_code"),
        "error_message": result.get("error_message"),
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


def _build_extract_from_chunk(item: dict) -> str:
    """Build a short extractive line from a retrieved chunk."""
    metadata = item.get("metadata", {})
    path = metadata.get("path", "unknown")
    start_line = metadata.get("start_line")
    end_line = metadata.get("end_line")
    line_span = (
        f"{path}:{start_line}"
        if start_line == end_line and start_line is not None
        else f"{path}:{start_line}-{end_line}"
        if start_line is not None and end_line is not None
        else path
    )
    snippet = re.sub(r"\s+", " ", item.get("content", "").strip())
    if len(snippet) > 220:
        snippet = snippet[:217].rsplit(" ", 1)[0] + "..."
    return f"- {line_span}: {snippet}"


def _build_fallback_extractive_answer(citation_chunks: list[dict]) -> str:
    """Assemble a safe fallback answer from retrieved evidence."""
    extracts = [_build_extract_from_chunk(item) for item in citation_chunks[:3]]
    return "\n".join([FALLBACK_PREFIX, *extracts]).strip()


def _is_unusable_model_answer(answer_text: str) -> bool:
    """Return True when the model answer should be replaced by a safer fallback."""
    normalized = answer_text.strip().lower()
    refusal_text = REFUSAL_TEXT.lower()
    return normalized == refusal_text or normalized.startswith(refusal_text)


def _retrieve_evidence(
    query: str,
    collection_name: str,
    mode: str,
    n_results: int,
) -> tuple[list[dict], dict, float]:
    """Fetch retrieval results and return them with latency measurements."""
    retrieval_started_at = perf_counter()
    retrieved_chunks, retrieval_diagnostics = retrieve_chunks(
        query=query,
        collection_name=collection_name,
        n_results=n_results,
        mode=mode,
        return_diagnostics=True,
    )
    retrieval_latency_ms = round((perf_counter() - retrieval_started_at) * 1000, 2)
    return retrieved_chunks, retrieval_diagnostics, retrieval_latency_ms


def _finalize_retrieval_failure(
    exc: RetrievalError,
    request_started_at: float,
    trace_context: dict,
    retrieval_latency_ms: float,
) -> dict:
    """Return a safe response payload when retrieval is unavailable."""
    result = _build_response(
        answer=RETRIEVAL_FAILURE_TEXT,
        citations=[],
        confidence="low",
        outcome="error",
        retrieval_diagnostics={
            "matched_intents": [],
            "fetch_count": 0,
            "raw_result_count": 0,
            "error_code": exc.error_code,
            "error_message": str(exc),
            **exc.diagnostics,
        },
        error_code=exc.error_code,
        error_message=str(exc),
    )
    return _finalize_result(
        result=result,
        trace_context=trace_context,
        trace_state={
            "request_started_at": request_started_at,
            "retrieval_latency_ms": retrieval_latency_ms,
            "retrieved_chunks": [],
            "cleaned_chunks": [],
            "retrieval_diagnostics": result["retrieval_diagnostics"],
        },
    )


def _prepare_evidence(
    request_started_at: float,
    retrieval_latency_ms: float,
    retrieved_chunks: list[dict],
    retrieval_diagnostics: dict,
) -> dict:
    """Clean retrieval results and prepare trace state for finalization."""
    cleaned_chunks, cleaning_diagnostics = clean_retrieved_chunks(
        retrieved_chunks,
        query_intents=set(retrieval_diagnostics.get("matched_intents", [])),
        return_diagnostics=True,
    )
    diagnostics = {
        **retrieval_diagnostics,
        "postprocess": cleaning_diagnostics,
    }
    return {
        "cleaned_chunks": cleaned_chunks,
        "citation_chunks": select_citation_chunks(cleaned_chunks),
        "retrieval_diagnostics": diagnostics,
        "trace_state": {
            "request_started_at": request_started_at,
            "retrieval_latency_ms": retrieval_latency_ms,
            "retrieved_chunks": retrieved_chunks,
            "cleaned_chunks": cleaned_chunks,
            "retrieval_diagnostics": diagnostics,
        },
    }


def _build_supported_answer(
    query: str,
    mode: str,
    citation_chunks: list[dict],
    retrieval_diagnostics: dict,
) -> dict:
    """Generate the grounded answer or an extractive fallback when needed."""
    citations = format_citations(citation_chunks)
    try:
        answer_text = write_grounded_answer(
            query=query,
            retrieved_chunks=citation_chunks,
            mode=mode,
        )
    except (LLMDependencyError, LLMInvocationError) as exc:
        return _build_response(
            answer=_build_fallback_extractive_answer(citation_chunks),
            citations=citations,
            confidence="medium",
            outcome="fallback_answered",
            retrieved_chunks=citation_chunks,
            retrieval_diagnostics=retrieval_diagnostics,
            error_code=exc.error_code,
            error_message=str(exc),
        )

    if _is_unusable_model_answer(answer_text):
        return _build_response(
            answer=_build_fallback_extractive_answer(citation_chunks),
            citations=citations,
            confidence="medium",
            outcome="fallback_answered",
            retrieved_chunks=citation_chunks,
            retrieval_diagnostics=retrieval_diagnostics,
            error_code="llm_unusable_response",
            error_message=(
                "LLM output was not safely grounded enough to return directly."
            ),
        )

    return _build_response(
        answer=answer_text,
        citations=citations,
        confidence="high",
        outcome="answered",
        retrieved_chunks=citation_chunks,
        retrieval_diagnostics=retrieval_diagnostics,
    )


def answer_question(
    query: str,
    collection_name: str,
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
        retrieved_chunks, retrieval_diagnostics, retrieval_latency_ms = _retrieve_evidence(
            query=query,
            collection_name=collection_name,
            mode=mode,
            n_results=n_results,
        )
    except RetrievalError as exc:
        return _finalize_retrieval_failure(
            exc=exc,
            request_started_at=request_started_at,
            trace_context=trace_context,
            retrieval_latency_ms=round(
                (perf_counter() - retrieval_started_at) * 1000,
                2,
            ),
        )

    evidence = _prepare_evidence(
        request_started_at=request_started_at,
        retrieval_latency_ms=retrieval_latency_ms,
        retrieved_chunks=retrieved_chunks,
        retrieval_diagnostics=retrieval_diagnostics,
    )

    if not has_enough_evidence(evidence["citation_chunks"]):
        result = _build_response(
            answer=REFUSAL_TEXT,
            citations=[],
            confidence="low",
            outcome="refused",
            retrieved_chunks=evidence["cleaned_chunks"],
            retrieval_diagnostics=evidence["retrieval_diagnostics"],
        )
        return _finalize_result(
            result=result,
            trace_context=trace_context,
            trace_state=evidence["trace_state"],
        )

    result = _build_supported_answer(
        query=query,
        mode=mode,
        citation_chunks=evidence["citation_chunks"],
        retrieval_diagnostics=evidence["retrieval_diagnostics"],
    )

    return _finalize_result(
        result=result,
        trace_context=trace_context,
        trace_state=evidence["trace_state"],
    )
