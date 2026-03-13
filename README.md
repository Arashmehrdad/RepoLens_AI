# RepoLens AI

RepoLens AI is a repository question-answering assistant for onboarding, debugging,
release reviews, and deployment walkthroughs. It clones a repository, filters and
indexes the useful files, retrieves grounded evidence with metadata-aware reranking,
answers with line-aware citations, and refuses when the evidence is weak.

`v0.5.0 - Evaluation and Production Robustness` turns the project into a stronger
portfolio-ready demo with versioned eval reports, clearer failure handling, more
predictable ingestion on noisy repositories, and more intentional release-mode
retrieval.

## Overview

RepoLens AI helps developers answer questions such as:

- How do I run this project locally?
- Which files control deployment?
- What changed in this release?
- Where should I look to debug API behavior?

The assistant is grounded by repository evidence, not generic guessing. Every
non-refusal answer is expected to carry 1-3 line-aware citations such as
`README.md:94-145` or `app/api/main.py:1-45`.

## What v0.5.0 Adds

- richer, versioned evaluation outputs under `data/evals/results/<version>/<timestamp>/`
- safer ingestion defaults for larger or noisier repositories
- structured application errors for clone, ingestion, retrieval, vector store, and LLM failures
- fallback extractive answers when retrieval succeeds but LLM generation is unavailable
- stronger release-mode evidence selection for changelogs, release notes, workflows,
  version files, package metadata, and deployment/config changes
- clearer API and UI diagnostics, including `outcome`, `error_code`, `error_message`,
  `trace_summary`, and retrieval diagnostics
- demo-ready docs and asset paths for screenshots or short recordings

## Architecture

1. `/ingest` clones the target repository into `data/repos/`.
2. File discovery filters out generated, binary, vendored, oversized, and noisy files.
3. Documents are loaded with path metadata such as `is_release_note`,
   `is_version_file`, `is_deployment_file`, `is_test_file`, and `is_tutorial_doc`.
4. Chunking preserves overlap plus line spans, section headings, and Python symbols.
5. Chunks are indexed in Chroma with retrieval metadata.
6. `/ask` retrieves, reranks, cleans, validates evidence, and either answers,
   falls back to extractive evidence, refuses, or returns a safe error payload.
7. Structured JSONL traces are written to `logs/traces.jsonl`.
8. Versioned eval results are written to `data/evals/results/`.

## Project Layout

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
    evals/
    repos/
    vector_store/
  docs/
    assets/
    demo/
  logs/
  tests/
  Dockerfile.api
  Dockerfile.ui
  docker-compose.yml
  pytest.ini
  README.md
  requirements.txt
```

## Local Setup

Requirements:

- Python 3.11
- Git on `PATH` for repository cloning
- A valid `GEMINI_API_KEY` for LLM-backed answers

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`.

Useful environment variables:

- `GEMINI_MODEL_NAME`
- `REPOLENS_API_BASE_URL`
- `REPOLENS_VECTOR_STORE_DIR`
- `REPOLENS_EMBEDDING_CACHE_DIR`
- `REPOLENS_MAX_FILES`
- `REPOLENS_MAX_FILE_SIZE_BYTES`
- `REPOLENS_MAX_TOTAL_BYTES`
- `REPOLENS_CHUNK_SIZE`
- `REPOLENS_CHUNK_OVERLAP`

## Local Run

Start the API:

```powershell
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

Start the UI in another terminal:

```powershell
streamlit run app/ui/home.py
```

Useful URLs:

- API docs: `http://127.0.0.1:8000/docs`
- API health: `http://127.0.0.1:8000/health`
- UI: `http://127.0.0.1:8501`

## Deployment

The repo is prepared for a simple two-service deployment:

- `Dockerfile.api` for FastAPI
- `Dockerfile.ui` for Streamlit
- `docker-compose.yml` for local or demo orchestration
- `.dockerignore` to keep images lean

Run locally with containers:

```powershell
docker compose up --build
```

Public deployment checklist:

1. Deploy the API service from `Dockerfile.api`.
2. Deploy the UI service from `Dockerfile.ui`.
3. Set `REPOLENS_API_BASE_URL` on the UI service to the public API URL.
4. Set `GEMINI_API_KEY` on the API service.
5. Mount or persist `data/` and `logs/` if you want indexes, eval outputs, and traces
   to survive restarts.
6. Allow one initial embedding-model download or pre-warm
   `REPOLENS_EMBEDDING_CACHE_DIR`.

## API Behavior

The API preserves the main answer contract:

- `answer`
- `citations`
- `confidence`

It now also returns structured fields that make failures easier to diagnose:

- `outcome`
- `error_code`
- `error_message`
- `trace_summary`
- `retrieval_diagnostics`

Possible `outcome` values:

- `answered`
- `fallback_answered`
- `refused`
- `error`

## Observability

Every `/ask` request appends one JSONL record to `logs/traces.jsonl`.

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
- `error_code`
- `error_message`

The UI renders the compact `trace_summary` and exposes retrieval diagnostics in an
expander for debugging demos.

## Retrieval Modes

### Onboarding mode

Optimized for setup, architecture, configuration, and general repository navigation.

### Debug mode

Allows test evidence when the query actually signals debugging or testing, and boosts
entrypoints, tracing paths, and relevant runtime/config files.

### Release mode

Release mode is intentionally more evidence-driven in v0.5.0. It boosts:

- changelogs and release notes
- version files and package metadata
- release and CI workflows
- deployment artifacts such as Docker, compose, and hosting config
- documentation and README sections that describe version, deployment, or release changes

This keeps release answers more focused and less noisy than generic prompt shaping alone.

## Evaluation

Eval cases live in `app/evals/eval_dataset.py` and include category, mode, expected
citations, refusal expectations, and confidence thresholds.

Run the eval suite:

```powershell
python -m app.evals.run_evals --version v0.5.0
```

Results are saved to:

```text
data/evals/results/v0.5.0/<timestamp>/
  summary.json
  cases.json
  report.md
```

This makes answer quality comparable across releases instead of overwriting a single file.

## End-to-End Example

Input question:

```text
How do I run this project locally?
```

Retrieved evidence:

- `README.md:107-150` explains local setup and run commands.
- `app/api/main.py:23-54` shows the API startup lifecycle and health route.
- `README.md:1-26` summarizes the product flow and grounded-answer behavior.

Final answer:

```text
Install the project dependencies, start the FastAPI app with uvicorn, and run the
Streamlit UI in a second terminal. For a single-command local workflow, use
docker compose up --build.
```

Citations:

- `README.md:107-150`
- `app/api/main.py:23-54`
- `README.md:1-26`

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
    "README.md",
    "app/api/main.py",
    "app/ui/home.py"
  ]
}
```

## Demo Assets

The repo now includes real demo/documentation paths:

- workflow guide: [`docs/demo/release-workflow.md`](docs/demo/release-workflow.md)
- asset manifest: [`docs/assets/asset-manifest.md`](docs/assets/asset-manifest.md)

Expected screenshot or GIF paths:

- `docs/assets/repolens-ui-home.png`
- `docs/assets/repolens-trace-summary.png`
- `docs/assets/repolens-release-mode.gif`

These files are intentionally not faked in the repository. The manifest documents what
each capture should show.

## Production Robustness Notes

- Repository cloning degrades cleanly when GitPython or the `git` executable is missing.
- Ingestion fails with structured limit errors instead of indexing an unpredictable subset.
- Retrieval failures return a safe low-confidence payload instead of crashing the request.
- LLM dependency or invocation failures fall back to extractive evidence when possible.
- Weak or uncitable evidence still triggers a refusal.

## Validation

Typical local validation commands:

```powershell
python -m pytest -q
python -m pylint app
python -m app.evals.run_evals --version v0.5.0
python -c "import app.api.main"
```

## v0.5.0 Release Summary

`v0.5.0 - Evaluation and Production Robustness`

Highlights:

- versioned evaluation outputs and release-friendly markdown reports
- safer ingestion and file filtering for large or noisy repositories
- stronger release-mode evidence handling
- structured API and UI failure diagnostics
- fallback extractive answers when LLM generation is unavailable
- demo-ready docs and asset paths

## Current Limits

- RepoLens AI still depends on repository text quality and chunked evidence coverage.
- Release intelligence is metadata-aware, but not git-history aware.
- The strongest section and symbol extraction is currently for Markdown and Python files.
- Public deployment still requires hosting credentials and environment-variable setup
  outside this repository.

## Author

Arash Mehrdad
