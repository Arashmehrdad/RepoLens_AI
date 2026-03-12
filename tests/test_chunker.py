"""Tests for document chunking."""

from app.retrieval.chunker import chunk_documents


def build_document(content: str) -> dict:
    """Create a retrieval document with the required metadata fields."""
    return {
        "content": content,
        "path": "README.md",
        "path_lower": "readme.md",
        "filename": "README.md",
        "filename_lower": "readme.md",
        "suffix": ".md",
        "stem": "readme",
        "parent_dirs": [],
        "parent_dirs_joined": "",
        "depth": 1,
        "is_readme": True,
        "is_config": False,
        "is_docker": False,
        "is_compose": False,
        "is_api": False,
        "is_app_entry": False,
        "is_training": False,
        "is_workflow": False,
        "is_dependency_file": False,
    }


def test_chunk_documents_splits_long_paragraphs_with_overlap():
    """Long paragraphs should be split with character overlap preserved."""
    source_text = "".join(str(index % 10) for index in range(140))

    chunks = chunk_documents([build_document(source_text)], chunk_size=100, chunk_overlap=20)

    assert len(chunks) == 2
    assert chunks[0]["content"] == source_text[:100]
    assert chunks[1]["content"].startswith(source_text[80:100])
    assert chunks[1]["chunk_index"] == 1


def test_chunk_documents_copies_document_metadata():
    """Chunk records should keep the metadata required for reranking and indexing."""
    chunks = chunk_documents([build_document("paragraph one\n\nparagraph two")], chunk_size=100)

    assert len(chunks) == 1
    assert chunks[0]["path"] == "README.md"
    assert chunks[0]["filename"] == "README.md"
    assert chunks[0]["is_readme"] is True
