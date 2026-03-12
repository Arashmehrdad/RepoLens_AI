"""Utility functions for shortening and cleaning text."""

import re


def clean_chunk_text(text: str, max_length: int = 300) -> str:
    """Normalize whitespace and truncate chunk text for display."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_length:
        text = text[:max_length].rstrip() + "..."

    return text
