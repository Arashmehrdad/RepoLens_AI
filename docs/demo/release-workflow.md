# RepoLens AI Demo Workflow

This document describes a polished, honest demo flow for RepoLens AI `v0.6.0`.
Use it when recording a GIF, taking screenshots, or preparing a portfolio walkthrough.

## Goal

Show that RepoLens AI can:

- ingest a real repo state
- answer with grounded line-aware citations
- compare two repo states with release-focused evidence
- surface traces, diagnostics, and eval regressions
- export a review report for handoff or release review
- fail safely when evidence or dependencies are weak

## Suggested Demo Sequence

### 1. Health and startup

Show:

- FastAPI running at `/docs`
- Streamlit UI loaded
- the configured API base URL caption in the UI

Suggested asset:

- `docs/assets/repolens-ui-home.png`

### 2. Ingest one repo state

Use a repo URL or local path such as:

```text
https://github.com/Arashmehrdad/RepoLens_AI
```

Optionally use a ref such as:

```text
v0.6.0
```

Show:

- successful ingest response
- ref-aware `collection_name`
- `state_id`
- `manifest_path`
- `incremental_stats`
- `ingestion_diagnostics` with selected file counts and skip reasons

### 3. Grounded Q&A

Ask:

```text
How do I run this project locally?
```

Show:

- grounded answer
- 1-3 line-aware citations
- confidence and outcome
- trace summary

Suggested citations to highlight if they appear:

- `README.md:<line range>`
- `app/api/main.py:<line range>`
- `app/ui/home.py:<line range>`

### 4. Release-mode question

Switch to release mode and ask:

```text
What changed in v0.6.0?
```

Show:

- release-focused evidence instead of generic code noise
- retrieval diagnostics surfacing changelog/docs/workflow/package signals
- top paths or top citations that are clearly release-relevant

Suggested asset:

- `docs/assets/repolens-release-mode.gif`

### 5. Compare two repo states

In the compare tab, compare two refs of the same repo:

```text
State A ref: v0.5.0
State B ref: v0.6.0
Question: What changed from v0.5.0 to v0.6.0, and what affects deployment?
```

Show:

- changed / added / removed file counts
- setup, deployment, and CI/CD impact lists
- cross-state citations such as `A: ...` and `B: ...`
- compare diagnostics including prioritized files and evidence coverage

Suggested asset:

- `docs/assets/repolens-compare-mode.png`

### 6. Export a review report

After running compare mode, generate a review report and show:

- markdown output
- JSON output
- saved paths under `data/reports/`

Suggested asset:

- `docs/assets/repolens-review-report.png`

### 7. Eval regressions

Open the eval regressions tab and show:

- per-version summaries
- pass rate, relevance, citation correctness, refusal correctness, and latency
- historical runs loaded from `data/evals/results/`

Suggested asset:

- `docs/assets/repolens-regression-dashboard.png`

### 8. Safe failure behavior

Demonstrate one safe failure mode:

- ask an out-of-scope question and show refusal
- or temporarily remove `GEMINI_API_KEY` and show fallback extractive answering

Show:

- `outcome`
- `confidence`
- `error_code`
- `error_message` when applicable

## Recording Notes

- Keep repo URLs, refs, citations, and diagnostics readable in the capture.
- Avoid editing files live during the recording unless the demo is specifically about
  debugging retrieval or compare behavior.
- If the embedding model downloads on first run, pre-warm the cache before recording.
