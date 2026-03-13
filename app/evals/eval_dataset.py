"""Structured evaluation dataset for release-quality regression checks."""

EVAL_CASES = [
    {
        "name": "setup_local_run",
        "category": "small_python_app",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "How do I run this project locally?",
        "expected_citations": ["README.md", "app/api/main.py"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Baseline onboarding question that should cite setup docs and the "
            "API entrypoint. Fallback answers remain acceptable if they stay grounded."
        ),
    },
    {
        "name": "architecture_overview",
        "category": "small_python_app",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "How is this project structured?",
        "expected_citations": ["README.md"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Architecture answers should rely on README plus retrieval "
            "evidence from the repo overview."
        ),
    },
    {
        "name": "api_health_endpoint",
        "category": "api_service",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "What health endpoint does the API expose?",
        "expected_citations": ["app/api/main.py"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Simple API-service question that should resolve directly from "
            "FastAPI routes."
        ),
    },
    {
        "name": "debug_trace_flow",
        "category": "api_service",
        "collection_name": "repo_repolens_ai",
        "mode": "debug",
        "query": "Where should I look to inspect ask request tracing?",
        "expected_citations": ["app/api/main.py"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": "Debug mode should surface the ask route and trace-exposing API code.",
    },
    {
        "name": "ui_api_base_url",
        "category": "frontend_or_ui_repo",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "How does the UI choose the API base URL?",
        "expected_citations": ["app/ui/home.py"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "UI questions should cite Streamlit code instead of only README "
            "guidance."
        ),
    },
    {
        "name": "deployment_artifacts",
        "category": "infra_or_devops_repo",
        "collection_name": "repo_repolens_ai",
        "mode": "release",
        "query": "What deployment artifacts are available for this project?",
        "expected_citations": ["Dockerfile.api", "README.md"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Release mode should prioritize container and deployment assets "
            "over generic code."
        ),
    },
    {
        "name": "release_summary",
        "category": "infra_or_devops_repo",
        "collection_name": "repo_repolens_ai",
        "mode": "release",
        "query": "What changed in v0.5.0?",
        "expected_citations": ["README.md"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Release mode should combine docs and implementation evidence for "
            "shipped features."
        ),
    },
    {
        "name": "large_repo_test_signal",
        "category": "noisy_large_repo",
        "collection_name": "repo_repolens_ai",
        "mode": "debug",
        "query": "Which tests verify the ask endpoint response shape?",
        "expected_citations": ["tests/test_api_main.py"],
        "should_refuse": False,
        "minimum_confidence": "medium",
        "notes": (
            "Debug-style queries should allow test files to surface in noisier "
            "repositories."
        ),
    },
    {
        "name": "ml_training_refusal",
        "category": "ml_repo",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "Where is the model training loop and fine-tuning pipeline?",
        "expected_citations": [],
        "should_refuse": True,
        "expected_confidence": "low",
        "notes": (
            "The current repo is not an ML training codebase, so the "
            "assistant should refuse cleanly."
        ),
    },
    {
        "name": "out_of_scope_question",
        "category": "small_python_app",
        "collection_name": "repo_repolens_ai",
        "mode": "onboarding",
        "query": "What is the capital of France?",
        "expected_citations": [],
        "should_refuse": True,
        "expected_confidence": "low",
        "notes": "Out-of-repo questions should refuse with low confidence.",
    },
]
