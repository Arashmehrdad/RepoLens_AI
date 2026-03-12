"""Saved evaluation cases for quick regression checks."""

EVAL_CASES = [
    {
        "name": "setup_local_run",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "How do I run this project locally?",
        "expected_citations": ["README.md", "requirements.txt"],
        "should_refuse": False,
    },
    {
        "name": "architecture_overview",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "How is this project structured?",
        "expected_citations": ["README.md", "app/retrieval/retriever.py"],
        "should_refuse": False,
    },
    {
        "name": "debug_trace_flow",
        "collection_name": "repo_repolens_ai",
        "mode": "debug",
        "query": "Where should I look to inspect ask request tracing?",
        "expected_citations": ["app/core/tracing.py", "app/generation/answer_service.py"],
        "should_refuse": False,
    },
    {
        "name": "deployment_artifacts",
        "collection_name": "repo_repolens_ai",
        "mode": "release",
        "query": "What deployment artifacts are available for this project?",
        "expected_citations": ["docker-compose.yml", "Dockerfile.api", "Dockerfile.ui"],
        "should_refuse": False,
    },
    {
        "name": "release_summary",
        "collection_name": "repo_repolens_ai",
        "mode": "release",
        "query": "What changed in v0.4.0?",
        "expected_citations": ["README.md", "app/core/tracing.py", "app/retrieval/retriever.py"],
        "should_refuse": False,
    },
    {
        "name": "out_of_scope_question",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "What is the capital of France?",
        "expected_citations": [],
        "should_refuse": True,
    },
]
