"""Tests for document chunking."""

from app.retrieval.chunker import chunk_documents


def build_document(content: str, path: str = "README.md") -> dict:
    """Create a retrieval document with the required metadata fields."""
    filename = path.split("/")[-1]
    suffix = f".{filename.split('.')[-1]}" if "." in filename else ""

    return {
        "content": content,
        "path": path,
        "path_lower": path.lower(),
        "filename": filename,
        "filename_lower": filename.lower(),
        "suffix": suffix,
        "stem": filename.rsplit(".", maxsplit=1)[0].lower() if suffix else filename.lower(),
        "parent_dirs": path.split("/")[:-1],
        "parent_dirs_joined": "",
        "depth": len(path.split("/")),
        "is_readme": filename.lower().startswith("readme"),
        "is_config": False,
        "is_docker": False,
        "is_compose": False,
        "is_api": "api" in path.lower().split("/"),
        "is_app_entry": filename.rsplit(".", maxsplit=1)[0].lower() in {"main", "app", "server", "run", "manage"},
        "is_training": False,
        "is_workflow": False,
        "is_dependency_file": False,
        "is_changelog": False,
        "is_release_note": False,
        "is_version_file": False,
        "is_deployment_file": False,
        "is_docs_update": filename.lower().startswith("readme") or suffix == ".md",
        "is_architecture_doc": False,
        "is_test_file": False,
    }


def test_chunk_documents_splits_long_paragraphs_with_overlap():
    """Long paragraphs should be split with character overlap preserved."""
    source_text = "".join(str(index % 10) for index in range(140))

    chunks = chunk_documents([build_document(source_text)], chunk_size=100, chunk_overlap=20)

    assert len(chunks) == 2
    assert chunks[0]["content"] == source_text[:100]
    assert chunks[1]["content"].startswith(source_text[80:100])
    assert chunks[1]["chunk_index"] == 1
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 1
    assert chunks[1]["start_line"] == 1
    assert chunks[1]["end_line"] == 1


def test_chunk_documents_copies_document_metadata():
    """Chunk records should keep the metadata required for reranking and indexing."""
    chunks = chunk_documents([build_document("paragraph one\n\nparagraph two")], chunk_size=100)

    assert len(chunks) == 1
    assert chunks[0]["path"] == "README.md"
    assert chunks[0]["filename"] == "README.md"
    assert chunks[0]["is_readme"] is True
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 3


def test_chunk_documents_tracks_markdown_sections():
    """Markdown chunks should carry the nearest heading as section metadata."""
    content = "# Setup\n\nRun the app with uvicorn.\n"

    chunks = chunk_documents([build_document(content)], chunk_size=200)

    assert len(chunks) == 1
    assert chunks[0]["section"] == "Setup"
    assert chunks[0]["symbol"] == ""


def test_chunk_documents_tracks_python_symbols():
    """Python chunks should carry the nearest def or class symbol when available."""
    content = "def start_server():\n    return 'ok'\n"

    chunks = chunk_documents([build_document(content, path="app/api/main.py")], chunk_size=200)

    assert len(chunks) == 1
    assert chunks[0]["symbol"] == "start_server"
