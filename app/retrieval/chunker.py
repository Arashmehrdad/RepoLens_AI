"""Chunking utilities for repository documents."""

import re
from bisect import bisect_right

from app.core.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, MIN_CHUNK_CHARACTERS


def _empty_context() -> dict:
    """Return the default section and symbol context."""
    return {
        "section": "",
        "symbol": "",
    }


def _build_line_starts(text: str) -> list[int]:
    """Return the character offset where each 1-based line begins."""
    line_starts = [0]

    for match in re.finditer(r"\n", text):
        line_starts.append(match.end())

    return line_starts


def _line_number_for_offset(line_starts: list[int], offset: int) -> int:
    """Map a character offset back to a 1-based line number."""
    adjusted_offset = max(offset, 0)
    return bisect_right(line_starts, adjusted_offset) if line_starts else 1


def _build_line_contexts(lines: list[str], suffix: str) -> list[dict]:
    """Track the nearest heading or symbol for each file line."""
    current_section = ""
    current_symbol = ""
    contexts = []

    for line in lines:
        stripped_line = line.lstrip()

        if suffix == ".md":
            heading_match = re.match(r"#{1,6}\s+(.*)", stripped_line)
            if heading_match:
                current_section = heading_match.group(1).strip()

        if suffix == ".py":
            symbol_match = re.match(
                r"(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
                stripped_line,
            )
            if symbol_match:
                current_symbol = symbol_match.group(1)

        contexts.append(
            {
                "section": current_section,
                "symbol": current_symbol,
            }
        )

    return contexts


def _lookup_line_context(line_contexts: list[dict], line_number: int) -> dict:
    """Look up the nearest heading or symbol for a 1-based line number."""
    if not line_contexts:
        return _empty_context()

    return line_contexts[line_number - 1]


def _build_chunk_context(text: str, suffix: str) -> dict:
    """Collect reusable line metadata for a document."""
    return {
        "text": text,
        "line_starts": _build_line_starts(text),
        "line_contexts": _build_line_contexts(text.splitlines(), suffix),
    }


def _split_paragraphs(text: str, suffix: str) -> list[dict]:
    """Split a file into non-empty paragraph blocks with line metadata."""
    lines_with_endings = text.splitlines(keepends=True)
    plain_lines = text.splitlines()
    line_contexts = _build_line_contexts(plain_lines, suffix)
    paragraphs = []
    current_lines = []
    current_start_line = 0
    current_start_offset = 0
    current_offset = 0

    for line_number, line in enumerate(lines_with_endings, start=1):
        if line.strip():
            if not current_lines:
                current_start_line = line_number
                current_start_offset = current_offset
            current_lines.append(line)
        elif current_lines:
            context = _lookup_line_context(line_contexts, current_start_line)
            paragraphs.append(
                {
                    "start_offset": current_start_offset,
                    "end_offset": current_offset,
                    "start_line": current_start_line,
                    "end_line": line_number - 1,
                    **context,
                }
            )
            current_lines = []

        current_offset += len(line)

    if current_lines:
        context = _lookup_line_context(line_contexts, current_start_line)
        paragraphs.append(
            {
                "start_offset": current_start_offset,
                "end_offset": current_offset,
                "start_line": current_start_line,
                "end_line": len(lines_with_endings),
                **context,
            }
        )

    return paragraphs


def _build_chunk_record(
    document: dict,
    chunk_index: int,
    chunk_text: str,
    span_metadata: dict,
) -> dict:
    """Attach metadata to a single chunk."""
    return {
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
        **span_metadata,
        "is_readme": document["is_readme"],
        "is_config": document["is_config"],
        "is_docker": document["is_docker"],
        "is_compose": document["is_compose"],
        "is_api": document["is_api"],
        "is_app_entry": document["is_app_entry"],
        "is_training": document["is_training"],
        "is_workflow": document["is_workflow"],
        "is_dependency_file": document["is_dependency_file"],
        "is_changelog": document["is_changelog"],
        "is_release_note": document["is_release_note"],
        "is_version_file": document["is_version_file"],
        "is_deployment_file": document["is_deployment_file"],
        "is_docs_update": document["is_docs_update"],
        "is_architecture_doc": document["is_architecture_doc"],
        "is_test_file": document["is_test_file"],
        "is_example_file": document.get("is_example_file", False),
        "is_ci_file": document.get("is_ci_file", False),
        "is_package_config": document.get("is_package_config", False),
        "is_tutorial_doc": document.get("is_tutorial_doc", False),
    }


def _normalize_chunk_text(text: str) -> str:
    """Collapse whitespace for chunk deduplication and usefulness checks."""
    return re.sub(r"\s+", " ", text).strip()


def _is_useful_chunk_text(text: str) -> bool:
    """Return True when chunk text is substantive enough to keep."""
    normalized = _normalize_chunk_text(text)
    if not normalized:
        return False

    if len(normalized) >= MIN_CHUNK_CHARACTERS:
        return True

    return bool(re.search(r"[A-Za-z0-9]", normalized)) and len(normalized) >= 12


def _build_chunk_from_offsets(
    document: dict,
    chunk_context: dict,
    chunk_index: int,
    start_offset: int,
    end_offset: int,
) -> dict | None:
    """Create a chunk record from raw file offsets."""
    text = chunk_context["text"]
    chunk_text = text[start_offset:end_offset].strip()
    if not _is_useful_chunk_text(chunk_text):
        return None

    start_line = _line_number_for_offset(chunk_context["line_starts"], start_offset)
    end_line = _line_number_for_offset(
        chunk_context["line_starts"],
        max(start_offset, end_offset - 1),
    )
    span_metadata = {
        "start_line": start_line,
        "end_line": end_line,
        **_lookup_line_context(chunk_context["line_contexts"], start_line),
    }

    return _build_chunk_record(
        document=document,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        span_metadata=span_metadata,
    )


def _append_chunk_if_distinct(
    document_chunks: list[dict],
    seen_signatures: set[str],
    chunk_record: dict | None,
) -> bool:
    """Append a chunk only when it is non-empty and not a near-duplicate."""
    if chunk_record is None:
        return False

    normalized_text = _normalize_chunk_text(chunk_record["content"])
    signature = normalized_text[:240]
    if signature in seen_signatures:
        return False

    seen_signatures.add(signature)
    document_chunks.append(chunk_record)
    return True


def _chunk_long_paragraph(
    document: dict,
    chunk_context: dict,
    paragraph: dict,
    chunk_index: int,
    chunk_settings: dict,
) -> tuple[list[dict], int]:
    """Chunk a single long paragraph with character overlap."""
    parts = []
    seen_signatures = set()
    start = paragraph["start_offset"]
    step = max(1, chunk_settings["chunk_size"] - chunk_settings["chunk_overlap"])
    paragraph_end = paragraph["end_offset"]

    while start < paragraph_end:
        end = min(start + chunk_settings["chunk_size"], paragraph_end)
        chunk_record = _build_chunk_from_offsets(
            document=document,
            chunk_context=chunk_context,
            chunk_index=chunk_index,
            start_offset=start,
            end_offset=end,
        )
        if _append_chunk_if_distinct(parts, seen_signatures, chunk_record):
            chunk_index += 1

        if end >= paragraph_end:
            break
        start += step

    return parts, chunk_index


def _chunk_single_document(document: dict, chunk_settings: dict) -> list[dict]:
    """Chunk a single document while preserving line-aware metadata."""
    text = document["content"]
    if not text or not text.strip():
        return []

    chunk_context = _build_chunk_context(text, document["suffix"])
    paragraphs = _split_paragraphs(text, document["suffix"])
    if not paragraphs:
        return []

    document_chunks = []
    seen_signatures = set()
    chunk_index = 0
    current_chunk = {}

    for paragraph in paragraphs:
        paragraph_text = text[paragraph["start_offset"]:paragraph["end_offset"]].strip()
        if not current_chunk:
            if len(paragraph_text) > chunk_settings["chunk_size"]:
                paragraph_chunks, chunk_index = _chunk_long_paragraph(
                    document=document,
                    chunk_context=chunk_context,
                    paragraph=paragraph,
                    chunk_index=chunk_index,
                    chunk_settings=chunk_settings,
                )
                document_chunks.extend(paragraph_chunks)
            else:
                current_chunk = {
                    "start_offset": paragraph["start_offset"],
                    "end_offset": paragraph["end_offset"],
                }
            continue

        candidate_text = text[current_chunk["start_offset"]:paragraph["end_offset"]].strip()
        if len(candidate_text) <= chunk_settings["chunk_size"]:
            current_chunk["end_offset"] = paragraph["end_offset"]
            continue

        chunk_record = _build_chunk_from_offsets(
            document=document,
            chunk_context=chunk_context,
            chunk_index=chunk_index,
            start_offset=current_chunk["start_offset"],
            end_offset=current_chunk["end_offset"],
        )
        if _append_chunk_if_distinct(document_chunks, seen_signatures, chunk_record):
            chunk_index += 1

        if len(paragraph_text) > chunk_settings["chunk_size"]:
            paragraph_chunks, chunk_index = _chunk_long_paragraph(
                document=document,
                chunk_context=chunk_context,
                paragraph=paragraph,
                chunk_index=chunk_index,
                chunk_settings=chunk_settings,
            )
            document_chunks.extend(paragraph_chunks)
            current_chunk = {}
            continue

        current_chunk = {
            "start_offset": max(
                current_chunk["end_offset"] - chunk_settings["chunk_overlap"],
                current_chunk["start_offset"],
            ),
            "end_offset": paragraph["end_offset"],
        }

    if current_chunk:
        chunk_record = _build_chunk_from_offsets(
            document=document,
            chunk_context=chunk_context,
            chunk_index=chunk_index,
            start_offset=current_chunk["start_offset"],
            end_offset=current_chunk["end_offset"],
        )
        _append_chunk_if_distinct(document_chunks, seen_signatures, chunk_record)

    return document_chunks


def chunk_documents(
    documents: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Chunk documents with overlap across adjacent chunk boundaries."""
    chunks = []
    chunk_settings = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }

    for document in documents:
        chunks.extend(_chunk_single_document(document, chunk_settings))

    return chunks
