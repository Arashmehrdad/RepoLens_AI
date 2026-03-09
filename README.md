# RepoLens AI

RepoLens AI is an evaluated GitHub codebase assistant that ingests a repository, retrieves relevant evidence, answers questions with file-level citations, and refuses when the evidence is weak.

## Why this project exists

Developers waste time trying to understand unfamiliar repositories. RepoLens AI is designed to accelerate codebase onboarding by answering repository-specific questions with grounded retrieval, explicit citations, confidence signaling, and refusal behavior when support is insufficient.

## Core features

* GitHub repository ingestion from URL
* File parsing for useful repository documents
* Chunking and vector indexing with Chroma
* Retrieval-based question answering
* File-level citations
* Evidence-gated refusal behavior
* Multiple answer modes:

  * onboarding
  * debug
  * release
* Trace logging
* Small evaluation pipeline with saved results

## Current tech stack

* FastAPI
* Streamlit
* Chroma
* GitPython
* Gemini API
* Python

## Current project structure

```text
repolens-ai/
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
  README.md
  requirements.txt
```

## Example workflow

1. User submits a GitHub repository URL
2. RepoLens AI clones and parses the repository
3. Supported files are chunked and indexed
4. The user asks a repository question
5. Relevant chunks are retrieved
6. The system answers using only retrieved evidence
7. If evidence is weak, the system refuses
8. The response is logged and can be evaluated

## Example questions

* How do I run this project?
* Where is the model training logic?
* What files are most relevant to deployment?
* Where should I look if I want to change how the development server starts?

## Evaluation status

Current saved evaluation results are stored in:

```text
data/eval_results.json
```

Current trace logs are stored in:

```text
logs/traces.jsonl
```

## Current limitations

* Retrieval quality still depends on chunking and repository structure
* Release mode is prompt-shaped, not commit-aware yet
* Citations are file-level with chunk references, not line ranges
* Large repositories may need better filtering and indexing strategy

## Next priorities

* Improve retrieval precision
* Add line-range style citations if feasible
* Improve release-mode evidence selection
* Add latency metrics to traces
* Prepare deployment

## Author

Arash Mehrdad
