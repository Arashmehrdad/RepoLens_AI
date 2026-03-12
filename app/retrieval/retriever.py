"""Query retrieval with intent-aware reranking."""

from app.retrieval.vector_store import get_vector_collection


QUERY_INTENT_RULES = {
    "setup": {
        "keywords": {
            "run",
            "start",
            "setup",
            "install",
            "launch",
            "execute",
            "serve",
            "server",
            "dev server",
            "development server",
            "how do i run",
        },
        "boosts": {
            "is_readme": 2.8,
            "is_config": 1.6,
            "is_dependency_file": 1.5,
            "is_app_entry": 1.8,
            "is_api": 1.2,
        },
        "path_terms": {
            "readme": 2.0,
            "config": 1.2,
            "main": 1.2,
            "app": 1.1,
            "api": 1.1,
            "requirements": 1.3,
            "pyproject": 1.3,
        },
    },
    "training": {
        "keywords": {
            "train",
            "training",
            "fit",
            "model",
            "trainer",
            "learn",
            "fine-tune",
            "fine tune",
        },
        "boosts": {
            "is_training": 2.8,
            "is_config": 0.8,
        },
        "path_terms": {
            "train": 2.0,
            "trainer": 1.8,
            "model": 1.4,
            "pipeline": 1.0,
        },
    },
    "deployment": {
        "keywords": {
            "deploy",
            "deployment",
            "docker",
            "container",
            "compose",
            "workflow",
            "ci",
            "cd",
            "production",
            "hosting",
        },
        "boosts": {
            "is_docker": 2.6,
            "is_compose": 2.4,
            "is_workflow": 2.0,
            "is_config": 1.2,
            "is_api": 1.1,
            "is_app_entry": 1.0,
        },
        "path_terms": {
            "docker": 2.0,
            "compose": 1.9,
            ".github/workflows": 1.8,
            "config": 1.1,
            "api": 0.8,
            "main": 0.8,
        },
    },
    "api": {
        "keywords": {
            "api",
            "endpoint",
            "route",
            "fastapi",
            "request",
            "response",
            "startup",
        },
        "boosts": {
            "is_api": 2.5,
            "is_app_entry": 1.7,
            "is_config": 0.8,
        },
        "path_terms": {
            "api": 2.0,
            "main": 1.6,
            "app": 1.2,
            "schemas": 1.1,
        },
    },
    "config": {
        "keywords": {
            "config",
            "setting",
            "settings",
            "environment",
            "env",
            "variable",
            "variables",
        },
        "boosts": {
            "is_config": 2.4,
            "is_dependency_file": 1.2,
        },
        "path_terms": {
            "config": 2.0,
            "settings": 1.8,
            "env": 1.7,
            "requirements": 1.0,
            "pyproject": 1.0,
        },
    },
}


def classify_query_intents(query: str) -> set[str]:
    """Infer high-level repository intents from the user query."""
    query_lower = query.lower()
    intents = set()

    for intent_name, rule in QUERY_INTENT_RULES.items():
        if any(keyword in query_lower for keyword in rule["keywords"]):
            intents.add(intent_name)

    if not intents:
        if "config" in query_lower:
            intents.add("config")

    return intents


def compute_rerank_score(item: dict, intents: set[str]) -> float:
    """Combine semantic distance with path-aware heuristic boosts."""
    metadata = item.get("metadata", {})
    path_lower = metadata.get("path_lower", "")
    filename_lower = metadata.get("filename_lower", "")
    distance = item.get("distance")

    base_score = 1.0 / (1.0 + max(distance or 0.0, 0.0))
    boost_score = 0.0

    for intent in intents:
        rule = QUERY_INTENT_RULES[intent]

        for metadata_field, boost_value in rule["boosts"].items():
            if metadata.get(metadata_field):
                boost_score += boost_value

        for term, boost_value in rule["path_terms"].items():
            if term in path_lower or term in filename_lower:
                boost_score += boost_value

    if metadata.get("is_readme"):
        boost_score += 0.25

    if metadata.get("chunk_index") == 0:
        boost_score += 0.15

    return base_score + boost_score


def retrieve_chunks(
    query: str,
    collection_name: str = "repo_chunks",
    n_results: int = 5,
) -> list[dict]:
    """Retrieve chunks using vector search followed by intent-aware reranking."""
    collection = get_vector_collection(collection_name)

    fetch_count = max(n_results * 4, 12)
    results = collection.query(query_texts=[query], n_results=fetch_count)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []
    intents = classify_query_intents(query)

    retrieved_chunks = []
    for index, document in enumerate(documents):
        item = {
            "content": document,
            "metadata": metadatas[index],
            "distance": distances[index] if index < len(distances) else None,
        }
        item["rerank_score"] = compute_rerank_score(item, intents)
        item["matched_intents"] = sorted(intents)
        retrieved_chunks.append(item)

    retrieved_chunks.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
    return retrieved_chunks[:n_results]
