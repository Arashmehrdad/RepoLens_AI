"""Streamlit UI for RepoLens AI."""

# pylint: disable=duplicate-code

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
    retrieval_column.metric(
        "Retrieval Latency",
        f"{trace_summary['retrieval_latency_ms']} ms",
    )
    citation_column.metric("Citations", str(trace_summary["citations_count"]))
    st.json(trace_summary)


def render_retrieval_diagnostics(retrieval_diagnostics: dict | None) -> None:
    """Render retrieval diagnostics when they are available."""
    if not retrieval_diagnostics:
        return

    with st.expander("Retrieval Diagnostics", expanded=False):
        st.json(retrieval_diagnostics)


def render_compare_diagnostics(diagnostics: dict | None) -> None:
    """Render compare-mode diagnostics when they are available."""
    if not diagnostics:
        return

    with st.expander("Compare Diagnostics", expanded=False):
        st.json(diagnostics)


def build_status_banner(response_payload: dict) -> tuple[str, str]:
    """Return a banner tone and message for an ask response."""
    outcome = response_payload.get("outcome", "answered")
    confidence = response_payload.get("confidence", "low")
    error_message = response_payload.get("error_message")

    if outcome == "answered":
        return "success", f"Answered with {confidence} confidence."

    if outcome == "fallback_answered":
        return (
            "warning",
            error_message or "Returned a fallback answer from retrieved evidence.",
        )

    if outcome == "refused":
        return "info", "Refused because the repository evidence was too weak."

    return "error", error_message or "The request completed with a retrieval error."


def build_compare_status_banner(response_payload: dict) -> tuple[str, str]:
    """Return a banner tone and message for compare and release-diff responses."""
    outcome = response_payload.get("outcome", "weak_compare")
    confidence = response_payload.get("confidence", "low")

    if outcome == "compared":
        return "success", f"Compared both repo states with {confidence} confidence."

    return (
        "warning",
        response_payload.get("error_message")
        or "Comparison completed with weak grounded evidence.",
    )


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


def build_compare_request_payload(**compare_inputs) -> dict:
    """Return the request payload shared by compare and report actions."""
    return {
        "repo_url_a": compare_inputs["repo_url_a"].strip(),
        "repo_url_b": compare_inputs["repo_url_b"].strip(),
        "ref_a": compare_inputs["ref_a"].strip() or None,
        "ref_b": compare_inputs["ref_b"].strip() or None,
        "query": compare_inputs["query"].strip() or None,
        "mode": compare_inputs["mode"],
    }


def summarize_regression_versions(regression_payload: dict) -> list[dict]:
    """Return a compact table-friendly regression summary."""
    return [
        {
            "version": item["version"],
            "runs": item["run_count"],
            "latest_pass_rate": item["latest_pass_rate"],
            "latest_relevance": item["latest_relevance_proxy_score"],
            "latest_citation": item["latest_citation_correctness"],
            "latest_refusal": item["latest_refusal_correctness"],
            "latest_latency_ms": item["latest_latency_avg_ms"],
        }
        for item in regression_payload.get("versions", [])
    ]


def _render_error(prefix: str, response: httpx.Response) -> None:
    """Render a structured API error response."""
    error_code, error_message = extract_error_details(response)
    if error_code:
        st.error(f"{prefix} [{error_code}]: {error_message}")
    else:
        st.error(f"{prefix}: {error_message}")


def handle_ingest(api_base_url: str, repo_url: str, ref: str) -> None:
    """Send the ingest request and render the result."""
    if not repo_url.strip():
        st.warning("Please enter a repository URL or local path.")
        return

    with st.spinner("Ingesting repository state..."):
        response = httpx.post(
            f"{api_base_url}/ingest",
            json={
                "repo_url": repo_url.strip(),
                "ref": ref.strip() or None,
            },
            timeout=120.0,
        )

    if response.status_code != 200:
        _render_error("Ingestion failed", response)
        return

    data = response.json()
    st.session_state.repo_url = repo_url.strip()
    st.session_state.repo_ref = ref.strip() or ""
    st.session_state.collection_name = data["collection_name"]
    st.success("Repository state ingested successfully.")
    st.json(data)


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
                "ref": st.session_state.get("repo_ref") or None,
                "mode": mode,
            },
            timeout=120.0,
        )

    if response.status_code != 200:
        _render_error("Question failed", response)
        return

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


def render_compare_result(data: dict) -> None:
    """Render a compare or release-diff response payload."""
    banner_tone, banner_message = build_compare_status_banner(data)
    getattr(st, banner_tone)(banner_message)

    st.subheader("Comparison Summary")
    st.write(data["answer"])

    status_column, confidence_column = st.columns(2)
    status_column.metric("Outcome", data.get("outcome", "weak_compare"))
    confidence_column.metric("Confidence", data.get("confidence", "low"))

    change_column, added_column, removed_column = st.columns(3)
    change_column.metric("Changed", len(data.get("changed_files", [])))
    added_column.metric("Added", len(data.get("added_files", [])))
    removed_column.metric("Removed", len(data.get("removed_files", [])))

    st.subheader("Cross-State Citations")
    for citation in data.get("citations", []):
        st.code(citation)

    with st.expander("Impact Review", expanded=True):
        st.write("Setup impact:", ", ".join(data.get("setup_impact", [])) or "None")
        st.write(
            "Deployment impact:",
            ", ".join(data.get("deployment_impact", [])) or "None",
        )
        st.write("CI/CD impact:", ", ".join(data.get("ci_cd_impact", [])) or "None")
        st.write(
            "Package/versioning impact:",
            ", ".join(data.get("package_impact", [])) or "None",
        )
        st.write(
            "API/runtime impact:",
            ", ".join(data.get("api_runtime_impact", [])) or "None",
        )

    render_compare_diagnostics(data.get("diagnostics"))


def handle_compare(api_base_url: str, **compare_inputs) -> None:
    """Send the compare request and render the response."""
    if not compare_inputs["repo_url_a"].strip() or not compare_inputs["repo_url_b"].strip():
        st.warning("Please provide both repository states to compare.")
        return

    endpoint = (
        "/release-diff"
        if compare_inputs["mode"] == "release_diff"
        else "/compare"
    )
    payload = build_compare_request_payload(**compare_inputs)
    with st.spinner("Comparing repository states..."):
        response = httpx.post(
            f"{api_base_url}{endpoint}",
            json=payload,
            timeout=180.0,
        )

    if response.status_code != 200:
        _render_error("Comparison failed", response)
        return

    data = response.json()
    st.session_state.last_compare_payload = payload
    st.session_state.last_compare_response = data
    render_compare_result(data)


def handle_review_report(api_base_url: str, compare_payload: dict) -> None:
    """Generate and render an exportable markdown and JSON review report."""
    if not compare_payload:
        st.warning("Run a comparison first so the report matches the selected states.")
        return

    with st.spinner("Generating review report..."):
        response = httpx.post(
            f"{api_base_url}/review-report",
            json=compare_payload,
            timeout=180.0,
        )

    if response.status_code != 200:
        _render_error("Report generation failed", response)
        return

    data = response.json()
    st.success("Review report generated successfully.")
    st.caption(f"Markdown path: {data['markdown_path']}")
    st.caption(f"JSON path: {data['json_path']}")
    st.code(data["markdown"], language="markdown")
    with st.expander("Report JSON", expanded=False):
        st.json(data["report"])


def render_regression_dashboard(data: dict) -> None:
    """Render the eval regression dashboard payload."""
    version_rows = summarize_regression_versions(data)
    if version_rows:
        st.subheader("Version Summary")
        st.table(version_rows)
    else:
        st.info("No eval regression runs were found.")

    if data.get("metric_series"):
        with st.expander("Metric Series", expanded=False):
            st.json(data["metric_series"])

    if data.get("runs"):
        with st.expander("All Runs", expanded=False):
            st.json(data["runs"])


def handle_regressions(api_base_url: str, versions_filter: str) -> None:
    """Request regression aggregates and render the result."""
    params = {}
    if versions_filter.strip():
        params["versions"] = versions_filter.strip()

    with st.spinner("Loading eval regressions..."):
        response = httpx.get(
            f"{api_base_url}/eval-regressions",
            params=params,
            timeout=120.0,
        )

    if response.status_code != 200:
        _render_error("Regression dashboard failed", response)
        return

    render_regression_dashboard(response.json())


def _initialize_session_state() -> None:
    """Populate the Streamlit session state with expected defaults."""
    defaults = {
        "collection_name": None,
        "repo_url": "",
        "repo_ref": "",
        "last_compare_payload": None,
        "last_compare_response": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_ask_tab(api_base_url: str) -> None:
    """Render the repository ingestion and grounded Q&A tab."""
    repo_url = st.text_input(
        "Repository URL or local path",
        value=st.session_state.get("repo_url", ""),
        placeholder="https://github.com/pallets/flask.git",
    )
    repo_ref = st.text_input(
        "Repo ref (optional)",
        value=st.session_state.get("repo_ref", ""),
        placeholder="main, v0.6.0, refs/tags/v0.6.0",
    )

    if st.button("Ingest Repository State"):
        handle_ingest(api_base_url, repo_url, repo_ref)

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


def _render_compare_tab(api_base_url: str) -> None:
    """Render the multi-repo compare and report-export tab."""
    left_column, right_column = st.columns(2)
    compare_inputs = {
        "repo_url_a": left_column.text_input(
            "State A repo URL or path",
            value=st.session_state.get("repo_url", ""),
            placeholder="https://github.com/example/project",
            key="compare_repo_url_a",
        ),
        "ref_a": left_column.text_input(
            "State A ref",
            value=st.session_state.get("repo_ref", ""),
            placeholder="main",
            key="compare_ref_a",
        ),
        "repo_url_b": right_column.text_input(
            "State B repo URL or path",
            value=st.session_state.get("repo_url", ""),
            placeholder="https://github.com/example/project",
            key="compare_repo_url_b",
        ),
        "ref_b": right_column.text_input(
            "State B ref",
            placeholder="v0.6.0",
            key="compare_ref_b",
        ),
        "mode": st.selectbox(
            "Compare mode",
            ["compare", "release_diff"],
            index=0,
            format_func=lambda value: (
                "Release diff" if value == "release_diff" else "Compare"
            ),
        ),
        "query": st.text_area(
            "Comparison question (optional)",
            placeholder="What changed from v0.5.0 to v0.6.0?",
            key="compare_query",
        ),
    }

    if st.button("Run Comparison"):
        handle_compare(api_base_url, **compare_inputs)

    if st.button("Export Review Report"):
        handle_review_report(
            api_base_url=api_base_url,
            compare_payload=st.session_state.get("last_compare_payload"),
        )

    if st.session_state.get("last_compare_response"):
        render_compare_result(st.session_state["last_compare_response"])


def _render_regressions_tab(api_base_url: str) -> None:
    """Render the eval regression dashboard tab."""
    versions_filter = st.text_input(
        "Version filter (optional, comma-separated)",
        placeholder="v0.5.0,v0.6.0",
    )
    if st.button("Load Eval Regressions"):
        handle_regressions(api_base_url, versions_filter)


def main() -> None:
    """Render the Streamlit application."""
    api_base_url = get_api_base_url()
    st.set_page_config(page_title="RepoLens AI", layout="wide")
    _initialize_session_state()

    st.title("RepoLens AI")
    st.write(
        "Grounded repository Q&A, release review, and multi-repo comparison with "
        "line-aware citations."
    )
    st.caption(f"API base URL: {api_base_url}")

    ask_tab, compare_tab, regressions_tab = st.tabs(
        ["Repository Q&A", "State Compare", "Eval Regressions"]
    )

    with ask_tab:
        _render_ask_tab(api_base_url)

    with compare_tab:
        _render_compare_tab(api_base_url)

    with regressions_tab:
        _render_regressions_tab(api_base_url)


if __name__ == "__main__":
    main()
