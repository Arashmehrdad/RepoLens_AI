import re


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict]:
    chunks = []

    for document in documents:
        text = document["content"].strip()

        if not text:
            continue

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", text)
            if paragraph.strip()
        ]

        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph

            if len(candidate) <= chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(
                        {
                            "content": current_chunk,
                            "path": document["path"],
                            "filename": document["filename"],
                            "suffix": document["suffix"],
                            "chunk_index": chunk_index,
                        }
                    )
                    chunk_index += 1

                if len(paragraph) <= chunk_size:
                    current_chunk = paragraph
                else:
                    start = 0
                    while start < len(paragraph):
                        end = start + chunk_size
                        chunk_text = paragraph[start:end]

                        chunks.append(
                            {
                                "content": chunk_text,
                                "path": document["path"],
                                "filename": document["filename"],
                                "suffix": document["suffix"],
                                "chunk_index": chunk_index,
                            }
                        )
                        chunk_index += 1

                        if end >= len(paragraph):
                            break

                        start += chunk_size - chunk_overlap

                    current_chunk = ""

        if current_chunk:
            chunks.append(
                {
                    "content": current_chunk,
                    "path": document["path"],
                    "filename": document["filename"],
                    "suffix": document["suffix"],
                    "chunk_index": chunk_index,
                }
            )

    return chunks