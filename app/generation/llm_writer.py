"""LLM-backed answer writing helpers."""

import os

from dotenv import load_dotenv
from google import genai

from app.generation.prompts import build_mode_prompt

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"


def write_grounded_answer(
    query: str,
    retrieved_chunks: list[dict],
    mode: str = "onboarding",
) -> str:
    """Generate an answer grounded in the highest-priority retrieved chunks."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    evidence_blocks = []
    for item in retrieved_chunks[:3]:
        path = item["metadata"]["path"]
        content = item["content"].strip()
        evidence_blocks.append(f"FILE: {path}\nCONTENT:\n{content}")

    evidence_text = "\n\n---\n\n".join(evidence_blocks)
    prompt = build_mode_prompt(mode=mode, query=query, evidence_text=evidence_text)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    return response.text.strip()
