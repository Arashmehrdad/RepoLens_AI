from pathlib import Path


def load_documents(file_paths: list[Path], repo_root: Path) -> list[dict]:
    documents = []

    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        documents.append(
            {
                "content": content,
                "path": str(file_path.relative_to(repo_root)),
                "filename": file_path.name,
                "suffix": file_path.suffix.lower(),
            }
        )

    return documents