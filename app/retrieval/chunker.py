"""Chunking utilities for repository documents."""

import re


def _split_paragraphs(text: str) -> list[str]:
    """Split a file into non-empty paragraph blocks."""
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def _chunk_long_paragraph(paragraph: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Chunk a single long paragraph with character overlap."""
    parts = []
    start = 0
    step = max(1, chunk_size - chunk_overlap)

    while start < len(paragraph):
        end = start + chunk_size
        parts.append(paragraph[start:end].strip())
        if end >= len(paragraph):
            break
        start += step

    return parts


def _build_chunk_records(document: dict, chunk_texts: list[str]) -> list[dict]:
    """Attach metadata to chunk texts."""
    records = []

    for chunk_index, chunk_text in enumerate(chunk_texts):
        records.append(
            {
                "content": chunk_text,
                "chunk_index": chunk_index,
                "path": document["path"],
                "path_lower": document["path_lower"],
                "filename": document["filename"],
                "filename_lower": document["filename_lower"],
                "suffix": document["suffix"],
                "stem": document["stem"],
                "parent_dirs": document["parent_dirs"],
                "parent_dirs_joined": document["parent_dirs_joined"],
                "depth": document["depth"],
                "is_readme": document["is_readme"],
                "is_config": document["is_config"],
                "is_docker": document["is_docker"],
                "is_compose": document["is_compose"],
                "is_api": document["is_api"],
                "is_app_entry": document["is_app_entry"],
                "is_training": document["is_training"],
                "is_workflow": document["is_workflow"],
                "is_dependency_file": document["is_dependency_file"],
            }
        )

    return records


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict]:
    """Chunk documents with overlap across adjacent chunk boundaries."""
    chunks = []

    for document in documents:
        text = document["content"].strip()
        if not text:
            continue

        paragraphs = _split_paragraphs(text)
        if not paragraphs:
            continue

        chunk_texts = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(paragraph) > chunk_size:
                if current_chunk:
                    chunk_texts.append(current_chunk.strip())
                    current_chunk = ""

                chunk_texts.extend(
                    _chunk_long_paragraph(paragraph, chunk_size, chunk_overlap)
                )
                continue

            candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph
            if len(candidate) <= chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunk_texts.append(current_chunk.strip())
                overlap_text = current_chunk[-chunk_overlap:].strip()
                current_chunk = (
                    f"{overlap_text}\n\n{paragraph}".strip()
                    if overlap_text
                    else paragraph
                )
            else:
                current_chunk = paragraph

        if current_chunk:
            chunk_texts.append(current_chunk.strip())

        chunks.extend(_build_chunk_records(document, chunk_texts))

    return chunks
