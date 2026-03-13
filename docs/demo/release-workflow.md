# RepoLens AI Demo Workflow

This document describes a polished, honest demo flow for RepoLens AI `v0.5.0`.
Use it when recording a GIF, taking screenshots, or preparing a portfolio walkthrough.

## Goal

Show that RepoLens AI can:

- ingest a real repository
- answer with line-aware citations
- expose trace and retrieval diagnostics
- handle release-oriented questions more precisely than generic repository QA
- fail safely when evidence or dependencies are weak

## Suggested Demo Sequence

### 1. Health and startup

Show:

- FastAPI running at `/docs`
- Streamlit UI loaded
- the configured API base URL caption in the UI

Suggested asset:

- `docs/assets/repolens-ui-home.png`

### 2. Ingest the repository

Use a repository URL such as:

```text
https://github.com/Arashmehrdad/RepoLens_AI
```

Show:

- successful ingest response
- repo-specific `collection_name`
- `ingestion_diagnostics` with selected file counts and skip reasons

### 3. Setup question

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

### 4. Release question

Switch to release mode and ask:

```text
What changed in v0.5.0?
```

Show:

- release-focused evidence instead of generic code noise
- retrieval diagnostics surfacing changelog/docs/workflow/package signals
- top paths or top citations that are clearly release-relevant

Suggested asset:

- `docs/assets/repolens-release-mode.gif`

### 5. Observability view

Expand retrieval diagnostics and show:

- request latency
- retrieval latency
- chunks retrieved and chunks after cleaning
- top paths or top citations
- matched intents

Suggested asset:

- `docs/assets/repolens-trace-summary.png`

### 6. Safe failure behavior

Demonstrate one safe failure mode:

- ask an out-of-scope question and show refusal
- or temporarily run without `GEMINI_API_KEY` and show fallback extractive answering

Show:

- `outcome`
- `confidence`
- `error_code`
- `error_message` when applicable

## Recording Notes

- Keep the repo URL, query, citations, and trace summary visible in the capture.
- Avoid editing files live during the recording unless the demo is specifically about
  debugging retrieval behavior.
- If the embedding model downloads on first run, pre-warm the cache before recording.
