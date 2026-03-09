from app.generation.answer_service import answer_question


if __name__ == "__main__":
    query = "How do I run the Flask development server?"
    result = answer_question(query)

    print("Answer:\n")
    print(result["answer"])

    print("\nCitations:")
    for citation in result["citations"]:
        print(citation)

    print(f"\nConfidence: {result['confidence']}")