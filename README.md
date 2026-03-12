# RepoLens AI

RepoLens AI is a repository question-answering assistant that ingests a codebase, retrieves evidence with metadata-aware reranking, answers with line-aware citations, and refuses when the evidence is weak.

v0.4.0 focuses on deployment readiness, observability, stronger release-mode retrieval, and better retrieval precision across setup, architecture, debug, release, and deployment questions.

## Why This Project Exists

Developers lose time when onboarding into unfamiliar repositories. RepoLens AI shortens that loop by:

- cloning and indexing a repository
- retrieving the most relevant evidence for a question
- answering with grounded, line-aware citations
- logging measurable request behavior for inspection
- refusing when it cannot support an answer with valid evidence

## What v0.4.0 Adds

- deployment-ready API and UI container artifacts
- environment-configured API base URL for the Streamlit UI
- structured JSONL trace logging with request IDs, timing, counts, and retrieval diagnostics
- stronger release-mode evidence selection driven by retrieval metadata
- improved intent-aware reranking for setup, architecture, debug, release, and deployment questions
- cleaner retrieval post-processing with smarter dedupe and conditional test-file inclusion

## Architecture And Flow

1. The API ingests a Git repository URL and clones the repo into `data/repos/`.
2. Supported files are loaded with path-aware metadata such as readme/config/deployment/release/test signals.
3. Files are chunked with overlap and line spans so each chunk can cite exact file lines.
4. Chunks are indexed in Chroma with ranking metadata.
5. A question hits `/ask`, which retrieves, reranks, cleans, and validates evidence.
6. If evidence is strong and line-aware citations are available, the LLM generates a grounded answer.
7. The API returns the answer, citations, confidence, and a compact trace summary.
8. A structured trace record is appended to `logs/traces.jsonl`.

## Current Stack

- FastAPI
- Streamlit
- Chroma
- GitPython
- Google Gemini API
- Docker
- Python 3.11

## Repository Layout

```text
RepoLens_AI/
  app/
    api/
    core/
    evals/
    generation/
    guardrails/
    ingestion/
    retrieval/
    ui/
  data/
  logs/
  tests/
  Dockerfile.api
  Dockerfile.ui
  docker-compose.yml
  README.md
  requirements.txt
```

## Local Setup

1. Create and activate a Python environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Copy the example environment file and set your key:

```powershell
Copy-Item .env.example .env
```

4. Set `GEMINI_API_KEY` in `.env`.

Optional environment variables:

- `GEMINI_MODEL_NAME`
- `REPOLENS_API_BASE_URL`
- `REPOLENS_VECTOR_STORE_DIR`
- `REPOLENS_EMBEDDING_CACHE_DIR`

## Local Run Instructions

Start the API:

```powershell
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

Start the UI in a second terminal:

```powershell
streamlit run app/ui/home.py
```

Useful local URLs:

- API docs: `http://127.0.0.1:8000/docs`
- API health: `http://127.0.0.1:8000/health`
- UI: `http://127.0.0.1:8501`

## Docker And Deployment

### Local container run

```powershell
docker compose up --build
```

This starts:

- the API on port `8000`
- the Streamlit UI on port `8501`

### Public deployment approach

The repo is prepared for a simple two-service deployment:

- deploy `Dockerfile.api` as the API service
- deploy `Dockerfile.ui` as the UI service
- set `REPOLENS_API_BASE_URL` on the UI service to the public API URL
- set `GEMINI_API_KEY` on the API service
- optionally set `REPOLENS_VECTOR_STORE_DIR` and `REPOLENS_EMBEDDING_CACHE_DIR` if your host needs custom writable paths
- persist `data/` and `logs/` if you want stored indexes and traces to survive restarts

Recommended low-friction options:

- Render
- Railway
- Fly.io
- any container host that supports two services or a compose-style setup

Important first-run note:

- the default Chroma embedding model may need one initial download before queries can run
- if your deployment environment blocks outbound network access, pre-warm `REPOLENS_EMBEDDING_CACHE_DIR` during image build or mount a cache volume with the model files already present

## Observability And Tracing

Every `/ask` request writes a JSONL trace record to:

```text
logs/traces.jsonl
```

Trace fields include:

- `timestamp`
- `request_id`
- `query`
- `mode`
- `collection_name`
- `outcome`
- `confidence`
- `request_latency_ms`
- `retrieval_latency_ms`
- `chunks_retrieved_count`
- `chunks_after_cleaning_count`
- `citations_count`
- `top_paths`
- `top_citations`
- `retrieval_diagnostics`

The API also returns a compact `trace_summary`, and the UI displays it after each answer.

The default Chroma embedding model cache is also redirected into the repo data directory so local runs and containers do not depend on a writable user-profile cache path.
If retrieval dependencies are unavailable, `/ask` now returns a clean `503` instead of a raw traceback.

## Retrieval Modes

### Onboarding mode

Best for setup, architecture, and "where do I start?" questions.

### Debug mode

Boosts app entrypoints, config, and relevant test/debug evidence. Test files stay excluded by default unless the query explicitly signals debugging or testing.

### Release mode

Release mode now leans on retrieval and evidence selection first, not just prompt style. It boosts:

- changelogs and release notes
- version files
- deployment and workflow files
- README/docs updates
- config changes that affect shipping or running the project

## End-To-End Example

Input question:

```text
How do I run this project locally?
```

Retrieved evidence:

- `requirements.txt:1-13` shows the Python dependencies that need to be installed.
- `Dockerfile.api:13` shows the API startup command.
- `Dockerfile.ui:14` shows the UI startup command.

Final answer:

```text
Install the Python dependencies from requirements.txt, then start the API with uvicorn and the UI with Streamlit. For a single-command local run, use docker compose up --build.
```

Citations:

- `requirements.txt:1-13`
- `Dockerfile.api:13`
- `Dockerfile.ui:14`

Trace summary:

```json
{
  "request_id": "example-request-id",
  "outcome": "answered",
  "confidence": "high",
  "request_latency_ms": 182.4,
  "retrieval_latency_ms": 24.7,
  "chunks_retrieved_count": 8,
  "chunks_after_cleaning_count": 3,
  "citations_count": 3,
  "query_intents": ["setup", "deployment"],
  "top_paths": [
    "requirements.txt",
    "Dockerfile.api",
    "Dockerfile.ui"
  ]
}
```

## Demo Assets

Suggested portfolio asset paths:

- `assets/demo/repolens-ui.png`
- `assets/demo/trace-summary.png`
- `assets/demo/release-mode.gif`

These are not bundled yet, but the paths are ready for screenshots or short demo recordings.

## Evaluation

Saved eval cases live in:

```text
app/evals/eval_dataset.py
```

Run the eval script with:

```powershell
python -m app.evals.run_evals
```

The eval runner now records per-case errors instead of crashing the whole run when prerequisites such as collections or API keys are missing.

## v0.4.0 Release Summary

`v0.4.0 - Deployment and Observability`

Highlights:

- deployment scaffolding for API and UI containers
- env-configured API/UI wiring
- structured request tracing with timings and retrieval diagnostics
- stronger release-mode evidence selection
- improved intent-aware reranking and dedupe behavior
- line-aware citations preserved end-to-end

## Current Limits

- repository cloning still depends on Git being available at clone time
- LLM-backed answers still require a valid `GEMINI_API_KEY`
- release signals are metadata-driven and heuristic, not git-commit aware
- section/symbol extraction is strongest for Markdown and Python files

## Author

Arash Mehrdad
