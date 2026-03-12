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
            "is_docs_update": 1.0,
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
        "section_terms": {
            "setup": 1.8,
            "install": 1.7,
            "quickstart": 1.6,
            "run": 1.5,
            "usage": 1.0,
        },
        "symbol_terms": {},
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
        "section_terms": {
            "training": 1.4,
            "model": 1.0,
        },
        "symbol_terms": {},
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
            "is_deployment_file": 2.4,
            "is_release_note": 0.6,
        },
        "path_terms": {
            "docker": 2.0,
            "compose": 1.9,
            ".github/workflows": 1.8,
            "config": 1.1,
            "api": 0.8,
            "main": 0.8,
            "deploy": 1.8,
            "helm": 1.6,
            "k8s": 1.6,
            "terraform": 1.4,
        },
        "section_terms": {
            "deployment": 1.6,
            "production": 1.3,
            "docker": 1.3,
        },
        "symbol_terms": {},
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
        "section_terms": {
            "api": 1.4,
            "endpoint": 1.2,
        },
        "symbol_terms": {
            "router": 1.0,
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
        "section_terms": {
            "configuration": 1.4,
            "environment": 1.2,
        },
        "symbol_terms": {},
    },
    "architecture": {
        "keywords": {
            "architecture",
            "structure",
            "overview",
            "organized",
            "components",
            "flow",
            "system",
            "how is this project structured",
        },
        "boosts": {
            "is_readme": 2.0,
            "is_docs_update": 1.5,
            "is_architecture_doc": 2.6,
            "is_api": 1.0,
            "is_app_entry": 0.8,
        },
        "path_terms": {
            "readme": 1.6,
            "docs": 1.3,
            "architecture": 2.0,
            "design": 1.7,
            "core": 1.0,
            "retrieval": 1.0,
            "generation": 1.0,
            "ingestion": 1.0,
        },
        "section_terms": {
            "architecture": 2.0,
            "overview": 1.7,
            "flow": 1.2,
            "structure": 1.2,
        },
        "symbol_terms": {},
    },
    "debug": {
        "keywords": {
            "debug",
            "bug",
            "issue",
            "error",
            "traceback",
            "failing",
            "failure",
            "broken",
            "problem",
            "investigate",
            "where should i look",
            "why does",
            "why is",
        },
        "boosts": {
            "is_api": 1.8,
            "is_app_entry": 1.5,
            "is_config": 1.0,
            "is_test_file": 1.2,
            "is_workflow": 0.6,
        },
        "path_terms": {
            "main": 1.4,
            "app": 1.2,
            "api": 1.2,
            "tests": 1.0,
            "logs": 0.8,
            "trace": 0.8,
        },
        "section_terms": {
            "debug": 1.2,
            "error": 1.1,
            "troubleshooting": 1.2,
        },
        "symbol_terms": {
            "start": 0.8,
            "run": 0.8,
            "load": 0.6,
        },
    },
    "testing": {
        "keywords": {
            "test",
            "tests",
            "testing",
            "pytest",
            "unit test",
            "integration test",
        },
        "boosts": {
            "is_test_file": 2.8,
            "is_workflow": 0.8,
        },
        "path_terms": {
            "tests": 2.0,
            "test_": 1.8,
            "pytest": 1.4,
        },
        "section_terms": {
            "testing": 1.3,
        },
        "symbol_terms": {
            "test": 1.4,
        },
    },
    "release": {
        "keywords": {
            "release",
            "releases",
            "change",
            "changes",
            "changed",
            "changelog",
            "release notes",
            "what changed",
            "latest",
            "update",
            "updated",
            "version",
            "versions",
        },
        "boosts": {
            "is_changelog": 3.0,
            "is_release_note": 2.8,
            "is_version_file": 2.2,
            "is_deployment_file": 1.6,
            "is_docs_update": 1.4,
            "is_workflow": 1.2,
            "is_config": 1.0,
            "is_readme": 0.8,
        },
        "path_terms": {
            "changelog": 2.5,
            "release": 2.2,
            "version": 1.9,
            "history": 1.8,
            "pyproject": 1.4,
            "package.json": 1.4,
            "docker": 1.0,
            "compose": 1.0,
        },
        "section_terms": {
            "release": 2.0,
            "changes": 1.7,
            "changelog": 2.0,
            "version": 1.5,
            "migration": 1.4,
            "deployment": 1.0,
        },
        "symbol_terms": {},
    },
}


MODE_DEFAULT_INTENTS = {
    "debug": {"debug"},
    "release": {"release"},
}


def classify_query_intents(query: str, mode: str | None = None) -> set[str]:
    """Infer high-level repository intents from the user query."""
    query_lower = query.lower()
    intents = set()

    if mode:
        intents.update(MODE_DEFAULT_INTENTS.get(mode.lower(), set()))

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
    section_lower = metadata.get("section", "").lower()
    symbol_lower = metadata.get("symbol", "").lower()
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

        for term, boost_value in rule["section_terms"].items():
            if term in section_lower:
                boost_score += boost_value

        for term, boost_value in rule["symbol_terms"].items():
            if term in symbol_lower:
                boost_score += boost_value

    if metadata.get("is_readme"):
        boost_score += 0.25

    if metadata.get("chunk_index") == 0:
        boost_score += 0.15

    if metadata.get("is_test_file") and not ({"debug", "testing"} & intents):
        boost_score -= 2.5

    return base_score + boost_score


def _build_retrieval_diagnostics(
    matched_intents: set[str],
    fetch_count: int,
    retrieved_chunks: list[dict],
) -> dict:
    """Build compact diagnostics for tracing and UI summaries."""
    top_candidates = []

    for item in retrieved_chunks[:5]:
        metadata = item.get("metadata", {})
        top_candidates.append(
            {
                "path": metadata.get("path"),
                "chunk_index": metadata.get("chunk_index"),
                "rerank_score": round(item.get("rerank_score", 0.0), 4),
                "distance": item.get("distance"),
            }
        )

    return {
        "matched_intents": sorted(matched_intents),
        "fetch_count": fetch_count,
        "raw_result_count": len(retrieved_chunks),
        "top_candidates": top_candidates,
    }


def _build_retrieved_chunks(results: dict, intents: set[str]) -> list[dict]:
    """Convert vector store results into reranked chunk payloads."""
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []
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

    return retrieved_chunks


def retrieve_chunks(
    query: str,
    collection_name: str = "repo_chunks",
    n_results: int = 5,
    mode: str | None = None,
    return_diagnostics: bool = False,
) -> list[dict] | tuple[list[dict], dict]:
    """Retrieve chunks using vector search followed by intent-aware reranking."""
    collection = get_vector_collection(collection_name)

    fetch_count = max(n_results * 4, 12)
    results = collection.query(query_texts=[query], n_results=fetch_count)
    intents = classify_query_intents(query, mode=mode)
    retrieved_chunks = _build_retrieved_chunks(results, intents)
    retrieved_chunks.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
    final_chunks = retrieved_chunks[:n_results]

    if not return_diagnostics:
        return final_chunks

    diagnostics = _build_retrieval_diagnostics(intents, fetch_count, retrieved_chunks)
    return final_chunks, diagnostics
