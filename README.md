# RepoLens AI

RepoLens AI is a grounded engineering assistant for repository Q&A, release review,
repo-state comparison, and evaluation regression tracking.

It ingests repository states, filters noisy files, indexes grounded evidence in Chroma,
retrieves and reranks chunks with line-aware citations, compares two repo states with
deterministic evidence-backed summaries, and exposes traces plus eval regressions for
debugging and release reviews.

`v0.6.0 - Multi-Repo Intelligence` extends the project from single-repo Q&A into a
stronger engineering workflow for:

- onboarding and setup questions
- debugging and architecture navigation
- release review and deployment impact analysis
- comparing two branches, tags, or repo refs
- tracking answer quality regressions across saved eval runs
- exporting review reports for handoff or release notes

## Core Capabilities

- Grounded repo Q&A with line-aware citations such as `README.md:107-150`
- Structured refusal and fallback behavior when evidence or LLM generation is weak
- Repo-state ingestion with ref-aware collection naming and incremental re-ingestion
- Multi-repo compare mode for changed, added, and removed file analysis
- Release diff mode that prioritizes changelogs, release notes, workflows, deployment files,
  version files, and package metadata
- Structured JSONL tracing for `/ask`
- Versioned eval reports plus a regression dashboard over historical runs
- Exportable compare review reports in both Markdown and JSON
- FastAPI API, Streamlit UI, and Docker-based deployment scaffolding

## v0.6.0 Highlights

- repo-state abstraction with deterministic `state_id`, `collection_name`, and `ref`
- compare and release-diff endpoints backed by grounded manifest and vector evidence
- incremental re-ingestion using saved manifests, file hashes, and stale chunk removal
- regression aggregation over `data/evals/results/<version>/<timestamp>/`
- review report export under `data/reports/`
- clearer diagnostics for noisy files, weak citations, compare evidence coverage, and
  incremental ingestion behavior
- Streamlit tabs for repository Q&A, state comparison, and eval regressions

## Architecture

### Q&A flow

1. `/ingest` resolves a repo URL or local path into a repo state.
2. File discovery filters binary, generated, vendored, oversized, and noisy files.
3. Document loading attaches metadata such as `is_release_note`, `is_workflow`,
   `is_package_config`, `is_deployment_file`, `is_test_file`, and `is_tutorial_doc`.
4. Chunking preserves overlap, line spans, Markdown headings, and Python symbols.
5. Chunks are indexed in a ref-aware Chroma collection.
6. `/ask` retrieves, reranks, cleans, validates evidence, and either:
   - answers
   - falls back to extractive evidence
   - refuses
   - or returns a structured error payload
7. Structured JSONL traces are written to `logs/traces.jsonl`.

### Compare flow

1. Two repo states are ingested independently.
2. Saved manifests are diffed by file path and content hash.
3. High-value files are prioritized using metadata and query intent.
4. Grounded evidence is loaded from both collections for the top changed files.
5. RepoLens returns:
   - changed / added / removed files
   - setup / deployment / CI/CD / package / API-runtime impacts
   - state-specific citations
   - compare diagnostics
6. `/review-report` exports the result as Markdown and JSON.

### Regression flow

1. `python -m app.evals.run_evals --version <version>` saves one eval run.
2. Saved results land under `data/evals/results/<version>/<timestamp>/`.
3. `/eval-regressions` aggregates historical runs into per-version summaries and metric series.
4. The Streamlit dashboard displays pass-rate, relevance, citation correctness, refusal
   correctness, and latency trends.

## Project Layout

```text
RepoLens_AI/
  app/
    api/
    comparison/
    core/
    evals/
    generation/
    guardrails/
    ingestion/
    reports/
    retrieval/
    ui/
  data/
    evals/results/
    manifests/
    reports/
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
  README.md
```

## Local Setup

Requirements:

- Python 3.11
- Git on `PATH` for remote cloning and non-default ref checkout
- A valid `GEMINI_API_KEY` if you want live model-written answers

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Set at least:

```env
GEMINI_API_KEY=your_key_here
```

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

Useful local URLs:

- API docs: `http://127.0.0.1:8000/docs`
- API health: `http://127.0.0.1:8000/health`
- UI: `http://127.0.0.1:8501`

## Deployment

RepoLens AI is prepared for a practical two-service deployment:

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
5. Persist `data/` and `logs/` if you want indexes, manifests, eval runs, reports, and traces
   to survive restarts.
6. Allow one initial embedding-model download or pre-warm
   `REPOLENS_EMBEDDING_CACHE_DIR`.

## API Surface

Primary endpoints:

- `POST /ingest`
- `POST /ask`
- `POST /compare`
- `POST /release-diff`
- `GET /eval-regressions`
- `POST /review-report`

The existing answer contract is preserved:

- `answer`
- `citations`
- `confidence`

RepoLens also returns structured fields such as:

- `outcome`
- `error_code`
- `error_message`
- `trace_summary`
- `retrieval_diagnostics`
- compare diagnostics and state metadata
- incremental ingestion stats

## Observability

Every `/ask` request appends one JSONL trace record to `logs/traces.jsonl`.

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

The UI renders a compact trace summary and expands retrieval diagnostics when needed.

## Retrieval and Compare Modes

### Onboarding mode

Optimized for setup, architecture, configuration, and general repo navigation.

### Debug mode

Allows test evidence when the query truly signals debugging or testing.

### Release mode

Prioritizes changelogs, release notes, version files, workflows, deployment files,
package metadata, and release-related README or docs updates.

### Compare mode

Diffs two repo states, prioritizes meaningful file classes, and returns grounded impact
summaries across:

- setup
- deployment
- CI/CD
- package/versioning
- API/runtime behavior

### Release diff mode

Adds stronger release-specific weighting on top of compare mode so release-review questions
focus on:

- `CHANGELOG` and release notes
- workflow and CI automation
- package and version metadata
- Docker, compose, and deployment config
- README/setup changes that affect the release experience

## Evaluation and Regressions

Eval cases live in `app/evals/eval_dataset.py` and now cover:

- setup
- architecture
- API behavior
- debug/test routing
- deployment
- release-mode retrieval
- compare-related implementation discovery
- regression aggregation discovery
- clean refusals

Run the eval suite:

```powershell
python -m app.evals.run_evals --version v0.6.0
```

Saved output layout:

```text
data/evals/results/v0.6.0/<timestamp>/
  summary.json
  cases.json
  report.md
```

The regression dashboard aggregates historical runs from those directories without assuming
perfect backward compatibility.

## End-to-End Example

Input question:

```text
How do I run this project locally?
```

Retrieved evidence:

- `README.md:107-150` covers local setup and run commands
- `app/api/main.py:23-54` shows API startup and health behavior
- `README.md:1-26` summarizes the product flow and grounded-answer contract

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
  "collection_name": "repo_repolens_ai",
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

## Compare Example

Example compare question:

```text
What changed from v0.5.0 to v0.6.0, and what affects deployment?
```

Expected grounded output shape:

- changed / added / removed files
- deployment and CI/CD impact lists
- citations from both states such as:
  - `A: README.md:10-24`
  - `B: .github/workflows/release.yml:2-20`
- optional review report export under `data/reports/`

## Demo Assets

Repo-based demo references:

- workflow guide: `docs/demo/release-workflow.md`
- asset manifest: `docs/assets/asset-manifest.md`

Expected asset paths:

- `docs/assets/repolens-ui-home.png`
- `docs/assets/repolens-compare-mode.png`
- `docs/assets/repolens-trace-summary.png`
- `docs/assets/repolens-regression-dashboard.png`
- `docs/assets/repolens-release-mode.gif`
- `docs/assets/repolens-review-report.png`

The repo intentionally does not include fake screenshots. The asset manifest documents what
real captures should show.

## Validation

Typical local validation commands:

```powershell
python -m pytest -q
python -m pylint app
python -m app.evals.run_evals --version v0.6.0
python -c "import app.api.main"
```

## v0.6.0 Release Summary

`v0.6.0 - Multi-Repo Intelligence`

Highlights:

- multi-repo compare and release-diff support across repo URLs and refs
- manifest-backed incremental re-ingestion with stale chunk cleanup
- regression dashboard aggregation across historical eval outputs
- exportable review reports in Markdown and JSON
- stronger compare and release diagnostics in the API and UI
- preserved grounded Q&A, line-aware citations, structured failures, and fallback behavior

## Current Limits

- Compare summaries are deterministic and grounded, but not git-history aware beyond the
  ingested repo states and retrieved evidence.
- The strongest section and symbol extraction is still for Markdown and Python files.
- Compare-mode tracing is more compact than `/ask` tracing; the main detailed trace stream
  still centers on Q&A requests.
- Public deployment still requires hosting credentials and environment-variable setup outside
  this repository.

## Author

Arash Mehrdad
