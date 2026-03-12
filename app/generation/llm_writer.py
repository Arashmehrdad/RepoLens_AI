"""LLM-backed answer writing helpers."""

import os

from dotenv import load_dotenv
from google import genai

from app.generation.prompts import build_mode_prompt

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


def _build_evidence_block(item: dict) -> str:
    """Format a retrieved chunk as an evidence block for the prompt."""
    metadata = item["metadata"]
    path = metadata["path"]
    start_line = metadata.get("start_line")
    end_line = metadata.get("end_line")
    section = metadata.get("section")
    symbol = metadata.get("symbol")
    content = item["content"].strip()
    line_span = (
        f"{start_line}-{end_line}"
        if start_line is not None and end_line is not None
        else "unknown"
    )
    context_lines = [f"FILE: {path}:{line_span}"]

    if section:
        context_lines.append(f"SECTION: {section}")

    if symbol:
        context_lines.append(f"SYMBOL: {symbol}")

    context_lines.append("CONTENT:")
    context_lines.append(content)
    return "\n".join(context_lines)


def write_grounded_answer(
    query: str,
    retrieved_chunks: list[dict],
    mode: str = "onboarding",
) -> str:
    """Generate an answer grounded in the highest-priority retrieved chunks."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    evidence_blocks = [_build_evidence_block(item) for item in retrieved_chunks[:3]]
    evidence_text = "\n\n---\n\n".join(evidence_blocks)
    prompt = build_mode_prompt(mode=mode, query=query, evidence_text=evidence_text)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    return response.text.strip()
