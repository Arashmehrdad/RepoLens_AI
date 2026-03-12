"""Citation formatting helpers."""

def format_citations(retrieved_chunks: list[dict]) -> list[str]:
    """Format unique chunk citations from retrieved results."""
    citations = []
    seen = set()

    for item in retrieved_chunks:
        metadata = item["metadata"]
        path = metadata["path"]
        chunk_index = metadata["chunk_index"]

        citation = f"{path} [chunk {chunk_index}]"

        if citation not in seen:
            seen.add(citation)
            citations.append(citation)

    return citations
