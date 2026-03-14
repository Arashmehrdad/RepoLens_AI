"""Repository-state helpers for multi-repo ingestion and comparison."""

# pylint: disable=duplicate-code

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

from app.core.config import MANIFESTS_DIR


def _safe_token(value: str) -> str:
    """Return a filesystem- and collection-safe token."""
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", value.lower()).strip("_")
    return normalized or "default"


def normalize_ref(ref: str | None) -> str:
    """Normalize a repository ref for deterministic state identities."""
    if not ref or not ref.strip():
        return "default"

    cleaned_ref = ref.strip()
    if cleaned_ref.lower().startswith("refs/heads/"):
        return cleaned_ref[11:]
    if cleaned_ref.lower().startswith("refs/tags/"):
        return cleaned_ref[10:]
    return cleaned_ref


def file_url_to_path(repo_url: str) -> Path:
    """Convert a local file URL into a filesystem path."""
    parsed_url = urlsplit(repo_url)
    raw_path = unquote(parsed_url.path)
    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    return Path(raw_path)


def normalize_repo_url(repo_url: str) -> str:
    """Normalize a repository URL or local path for deterministic naming."""
    cleaned_url = repo_url.strip()
    if not cleaned_url:
        raise ValueError("Repository URL must not be empty.")

    candidate_path = Path(cleaned_url)
    if "://" not in cleaned_url and candidate_path.exists():
        return candidate_path.resolve().as_posix()

    if "://" not in cleaned_url:
        return cleaned_url.rstrip("/").removesuffix(".git")

    parsed_url = urlsplit(cleaned_url)
    if parsed_url.scheme.lower() == "file":
        return file_url_to_path(cleaned_url).resolve().as_posix()

    normalized_path = parsed_url.path.rstrip("/").removesuffix(".git")
    return urlunsplit(
        (
            parsed_url.scheme.lower(),
            parsed_url.netloc.lower(),
            normalized_path,
            "",
            "",
        )
    )


def build_repo_name(repo_url: str) -> str:
    """Return the normalized repository name derived from a repo URL or path."""
    normalized_repo_url = normalize_repo_url(repo_url)
    return normalized_repo_url.split("/")[-1]


def build_collection_name(repo_url: str, ref: str | None = None) -> str:
    """Build a deterministic Chroma collection name for one repo state."""
    repo_name = build_repo_name(repo_url)
    safe_repo_name = _safe_token(repo_name)
    normalized_ref = normalize_ref(ref)

    if normalized_ref == "default":
        return f"repo_{safe_repo_name}"

    digest = hashlib.sha1(
        f"{normalize_repo_url(repo_url)}::{normalized_ref}".encode("utf-8")
    ).hexdigest()[:10]
    return f"repo_{safe_repo_name}__{_safe_token(normalized_ref)}_{digest}"


def build_state_id(repo_url: str, ref: str | None = None) -> str:
    """Build a deterministic state identifier for manifests and reports."""
    repo_name = build_repo_name(repo_url)
    normalized_ref = normalize_ref(ref)
    digest = hashlib.sha1(
        f"{normalize_repo_url(repo_url)}::{normalized_ref}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{_safe_token(repo_name)}__{_safe_token(normalized_ref)}__{digest}"


def build_manifest_path(state_id: str) -> Path:
    """Return the manifest path for a repo state."""
    return MANIFESTS_DIR / f"{state_id}.json"


def resolve_collection_name(
    repo_url: str | None = None,
    collection_name: str | None = None,
    ref: str | None = None,
) -> str:
    """Resolve the collection name used for repository question answering."""
    if repo_url and repo_url.strip():
        return build_collection_name(repo_url, ref=ref)

    if collection_name and collection_name.strip():
        return collection_name.strip()

    raise ValueError("Either repo_url or collection_name must be provided.")


@dataclass(slots=True)
class RepoState:
    """Serializable description of one ingested repository state."""
    # pylint: disable=too-many-instance-attributes

    repo_url: str
    repo_name: str
    normalized_repo_url: str
    ref: str
    state_id: str
    collection_name: str
    repo_path: str | None = None
    commit_sha: str | None = None
    manifest_path: str | None = None

    def to_dict(self) -> dict:
        """Return the repo state as a serializable dictionary."""
        return asdict(self)


def build_repo_state(
    repo_url: str,
    ref: str | None = None,
    repo_path: Path | None = None,
    commit_sha: str | None = None,
) -> RepoState:
    """Create the canonical repo-state object for one repository snapshot."""
    normalized_ref = normalize_ref(ref)
    state_id = build_state_id(repo_url, ref=normalized_ref)
    return RepoState(
        repo_url=repo_url,
        repo_name=build_repo_name(repo_url),
        normalized_repo_url=normalize_repo_url(repo_url),
        ref=normalized_ref,
        state_id=state_id,
        collection_name=build_collection_name(repo_url, ref=normalized_ref),
        repo_path=str(repo_path) if repo_path else None,
        commit_sha=commit_sha,
        manifest_path=str(build_manifest_path(state_id)),
    )
