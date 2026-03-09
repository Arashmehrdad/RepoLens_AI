from app.generation.llm_writer import write_grounded_answer
from app.retrieval.postprocess import clean_retrieved_chunks
from app.retrieval.retriever import retrieve_chunks


if __name__ == "__main__":
    query = "How do I run the Flask development server?"
    results = retrieve_chunks(
        query=query,
        collection_name="repo_flask",
        n_results=5,
    )
    cleaned = clean_retrieved_chunks(results)
    answer = write_grounded_answer(query, cleaned)

    print(answer)