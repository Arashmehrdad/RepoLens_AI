"""Saved evaluation cases for quick regression checks."""

EVAL_CASES = [
    {
        "name": "run_dev_server",
        "collection_name": "repo_flask",
        "mode": "onboarding",
        "query": "How do I run the Flask development server?",
        "expected_citations": ["src/flask/app.py", "README.md"],
        "should_refuse": False,
    },
    {
        "name": "debug_server_start",
        "collection_name": "repo_flask",
        "mode": "debug",
        "query": "Where should I look if I want to change how the development server starts?",
        "expected_citations": ["src/flask/app.py"],
        "should_refuse": False,
    },
    {
        "name": "out_of_scope_question",
        "collection_name": "repo_flask",
        "mode": "onboarding",
        "query": "What is the capital of France?",
        "expected_citations": [],
        "should_refuse": True,
    },
]
