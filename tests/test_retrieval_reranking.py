"""Tests for Milestone 2 retrieval behavior."""

from app.retrieval.retriever import classify_query_intents, compute_rerank_score


def build_item(path: str, **flags):
    metadata = {
        "path": path,
        "path_lower": path.lower(),
        "filename": path.split("/")[-1],
        "filename_lower": path.split("/")[-1].lower(),
        "chunk_index": 0,
        "is_readme": False,
        "is_config": False,
        "is_dependency_file": False,
        "is_app_entry": False,
        "is_api": False,
        "is_training": False,
        "is_docker": False,
        "is_compose": False,
        "is_workflow": False,
    }
    metadata.update(flags)
    return {
        "content": "dummy",
        "metadata": metadata,
        "distance": 0.4,
    }


def test_setup_query_detects_setup_intent():
    intents = classify_query_intents("How do I run this project?")
    assert "setup" in intents


def test_training_query_prefers_training_file_over_utils():
    intents = classify_query_intents("Where is model training logic?")
    train_item = build_item("app/train_model.py", is_training=True)
    util_item = build_item("app/utils/helpers.py")

    assert compute_rerank_score(train_item, intents) > compute_rerank_score(util_item, intents)


def test_deployment_query_prefers_docker_and_workflow_files():
    intents = classify_query_intents("What affects deployment?")
    docker_item = build_item("Dockerfile", is_docker=True)
    workflow_item = build_item(".github/workflows/deploy.yml", is_workflow=True)
    random_item = build_item("app/utils/helpers.py")

    assert compute_rerank_score(docker_item, intents) > compute_rerank_score(random_item, intents)
    assert compute_rerank_score(workflow_item, intents) > compute_rerank_score(random_item, intents)


def test_setup_query_prefers_readme_and_entrypoint():
    intents = classify_query_intents("How do I run this project?")
    readme_item = build_item("README.md", is_readme=True)
    main_item = build_item("app/api/main.py", is_api=True, is_app_entry=True)
    util_item = build_item("app/utils/strings.py")

    assert compute_rerank_score(readme_item, intents) > compute_rerank_score(util_item, intents)
    assert compute_rerank_score(main_item, intents) > compute_rerank_score(util_item, intents)
