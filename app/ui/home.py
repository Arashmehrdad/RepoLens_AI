import httpx
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="RepoLens AI", layout="wide")

st.title("RepoLens AI")
st.write("Ask questions about a GitHub repository with grounded citations.")

if "collection_name" not in st.session_state:
    st.session_state.collection_name = None

repo_url = st.text_input(
    "GitHub repository URL",
    placeholder="https://github.com/pallets/flask.git",
)

if st.button("Ingest Repository"):
    if not repo_url.strip():
        st.warning("Please enter a repository URL.")
    else:
        with st.spinner("Ingesting repository..."):
            response = httpx.post(
                f"{API_BASE_URL}/ingest",
                json={"repo_url": repo_url},
                timeout=120.0,
            )

        if response.status_code == 200:
            data = response.json()
            st.session_state.collection_name = data["collection_name"]
            st.success("Repository ingested successfully.")
            st.json(data)
        else:
            st.error(f"Ingestion failed: {response.text}")

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
    if not st.session_state.collection_name:
        st.warning("Please ingest a repository first.")
    elif not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Searching repository..."):
            response = httpx.post(
                f"{API_BASE_URL}/ask",
                json={
                    "query": question,
                    "collection_name": st.session_state.collection_name,
                    "mode": mode,
                },
                timeout=120.0,
            )

        if response.status_code == 200:
            data = response.json()

            st.subheader("Answer")
            st.write(data["answer"])

            st.subheader("Confidence")
            st.write(data["confidence"])

            st.subheader("Citations")
            for citation in data["citations"]:
                st.code(citation)
        else:
            st.error(f"Question failed: {response.text}")