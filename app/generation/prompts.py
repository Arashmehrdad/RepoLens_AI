def build_mode_prompt(mode: str, query: str, evidence_text: str) -> str:
    mode = mode.lower().strip()

    mode_instructions = {
        "onboarding": (
            "Explain the repository in a way that helps a new developer get started. "
            "Focus on setup, structure, important files, and how the project is run."
        ),
        "debug": (
            "Help the user investigate code behavior or likely problem areas. "
            "Focus on relevant files, functions, and configuration connected to the question."
        ),
        "release": (
            "Summarize the repository evidence from a release-oriented perspective. "
            "Focus on changes, configuration, docs, and deployment-related signals if present."
        ),
    }

    selected_instruction = mode_instructions.get(
        mode,
        mode_instructions["onboarding"],
    )

    return f"""
You are a repository assistant.

Answer the user's question using only the repository evidence below.
Do not invent files, functions, behavior, setup steps, or release details.
If the evidence is insufficient, say exactly:
I do not have enough evidence in the repository to answer that confidently.

Mode:
{mode}

Instruction:
{selected_instruction}

User question:
{query}

Repository evidence:
{evidence_text}

Write a concise answer grounded only in the evidence.
Do not include citations in the answer text.
""".strip()