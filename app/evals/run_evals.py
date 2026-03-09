import json
from pathlib import Path

from app.evals.eval_dataset import EVAL_CASES
from app.generation.answer_service import answer_question


REFUSAL_TEXT = "I do not have enough evidence in the repository to answer that confidently."
RESULTS_FILE = Path("data/eval_results.json")


def citation_hit(citations: list[str], expected_paths: list[str]) -> bool:
    return all(
        any(expected_path in citation for citation in citations)
        for expected_path in expected_paths
    )


if __name__ == "__main__":
    passed = 0
    results_summary = []

    for case in EVAL_CASES:
        result = answer_question(
            query=case["query"],
            collection_name=case["collection_name"],
            mode=case["mode"],
        )

        refused = result["answer"].strip() == REFUSAL_TEXT
        refusal_ok = refused == case["should_refuse"]
        citations_ok = citation_hit(result["citations"], case["expected_citations"])

        case_passed = refusal_ok and citations_ok

        case_result = {
            "name": case["name"],
            "query": case["query"],
            "mode": case["mode"],
            "answer": result["answer"],
            "citations": result["citations"],
            "confidence": result["confidence"],
            "refusal_ok": refusal_ok,
            "citations_ok": citations_ok,
            "passed": case_passed,
        }
        results_summary.append(case_result)

        print(f"\nCASE: {case['name']}")
        print("Answer:", result["answer"])
        print("Citations:", result["citations"])
        print("Confidence:", result["confidence"])
        print("Refusal OK:", refusal_ok)
        print("Citations OK:", citations_ok)
        print("PASS:", case_passed)

        if case_passed:
            passed += 1

    summary = {
        "passed": passed,
        "total": len(EVAL_CASES),
        "results": results_summary,
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nPassed {passed} / {len(EVAL_CASES)} cases")
    print(f"Saved results to {RESULTS_FILE}")