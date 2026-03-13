"""Streamlit UI for RepoLens AI."""

import os

import httpx
import streamlit as st

from app.core.env import load_environment


def get_api_base_url() -> str:
    """Return the configured API base URL with a safe local default."""
    load_environment()
    return os.getenv("REPOLENS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def render_trace_summary(trace_summary: dict | None) -> None:
    """Render the compact trace summary returned by the API."""
    if not trace_summary:
        return

    st.subheader("Trace Summary")
    st.caption(f"Request ID: {trace_summary['request_id']}")
    latency_column, retrieval_column, citation_column = st.columns(3)
    latency_column.metric("Request Latency", f"{trace_summary['request_latency_ms']} ms")
    retrieval_column.metric("Retrieval Latency", f"{trace_summary['retrieval_latency_ms']} ms")
    citation_column.metric("Citations", str(trace_summary["citations_count"]))
    st.json(trace_summary)


def render_retrieval_diagnostics(retrieval_diagnostics: dict | None) -> None:
    """Render retrieval diagnostics when they are available."""
    if not retrieval_diagnostics:
        return

    with st.expander("Retrieval Diagnostics", expanded=False):
        st.json(retrieval_diagnostics)


def build_status_banner(response_payload: dict) -> tuple[str, str]:
    """Return a banner tone and message for an ask response."""
    outcome = response_payload.get("outcome", "answered")
    confidence = response_payload.get("confidence", "low")
    error_message = response_payload.get("error_message")

    if outcome == "answered":
        return "success", f"Answered with {confidence} confidence."

    if outcome == "fallback_answered":
        return "warning", error_message or "Returned a fallback answer from retrieved evidence."

    if outcome == "refused":
        return "info", "Refused because the repository evidence was too weak."

    return "error", error_message or "The request completed with a retrieval error."


def extract_error_details(response: httpx.Response) -> tuple[str | None, str]:
    """Return a user-safe error code and message from an API response."""
    try:
        payload = response.json()
    except ValueError:
        return None, response.text

    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        return detail.get("error_code"), detail.get("error_message", response.text)

    return None, str(detail)


def handle_ingest(api_base_url: str, repo_url: str) -> None:
    """Send the ingest request and render the result."""
    if not repo_url.strip():
        st.warning("Please enter a repository URL.")
        return

    with st.spinner("Ingesting repository..."):
        response = httpx.post(
            f"{api_base_url}/ingest",
            json={"repo_url": repo_url},
            timeout=120.0,
        )

    if response.status_code == 200:
        data = response.json()
        st.session_state.repo_url = repo_url.strip()
        st.session_state.collection_name = data["collection_name"]
        st.success("Repository ingested successfully.")
        st.json(data)
    else:
        error_code, error_message = extract_error_details(response)
        if error_code:
            st.error(f"Ingestion failed [{error_code}]: {error_message}")
        else:
            st.error(f"Ingestion failed: {error_message}")


def handle_question(api_base_url: str, question: str, mode: str) -> None:
    """Send the ask request and render the answer payload."""
    if not st.session_state.collection_name:
        st.warning("Please ingest a repository first.")
        return

    if not question.strip():
        st.warning("Please enter a question.")
        return

    with st.spinner("Searching repository..."):
        response = httpx.post(
            f"{api_base_url}/ask",
            json={
                "query": question,
                "repo_url": st.session_state.get("repo_url"),
                "collection_name": st.session_state.collection_name,
                "mode": mode,
            },
            timeout=120.0,
        )

    if response.status_code == 200:
        data = response.json()
        banner_tone, banner_message = build_status_banner(data)
        getattr(st, banner_tone)(banner_message)

        st.subheader("Answer")
        st.write(data["answer"])

        status_column, confidence_column = st.columns(2)
        status_column.metric("Outcome", data.get("outcome", "answered"))
        confidence_column.metric("Confidence", data["confidence"])

        if data.get("error_code"):
            st.caption(f"Error code: {data['error_code']}")
        if data.get("error_message"):
            st.caption(data["error_message"])

        st.subheader("Citations")
        for citation in data["citations"]:
            st.code(citation)

        render_trace_summary(data.get("trace_summary"))
        render_retrieval_diagnostics(data.get("retrieval_diagnostics"))
    else:
        error_code, error_message = extract_error_details(response)
        if error_code:
            st.error(f"Question failed [{error_code}]: {error_message}")
        else:
            st.error(f"Question failed: {error_message}")


def main() -> None:
    """Render the Streamlit application."""
    api_base_url = get_api_base_url()
    st.set_page_config(page_title="RepoLens AI", layout="wide")

    st.title("RepoLens AI")
    st.write("Ask questions about a GitHub repository with grounded, line-aware citations.")
    st.caption(f"API base URL: {api_base_url}")

    if "collection_name" not in st.session_state:
        st.session_state.collection_name = None
    if "repo_url" not in st.session_state:
        st.session_state.repo_url = None

    repo_url = st.text_input(
        "GitHub repository URL",
        placeholder="https://github.com/pallets/flask.git",
    )

    if st.button("Ingest Repository"):
        handle_ingest(api_base_url, repo_url)

    mode = st.selectbox(
        "Mode",
        ["onboarding", "debug", "release"],
        index=0,
    )

    question = st.text_area(
        "Ask a question about the repository",
        placeholder="How do I run this project?",
    )

    if st.button("Ask Question"):
        handle_question(api_base_url, question, mode)


if __name__ == "__main__":
    main()
