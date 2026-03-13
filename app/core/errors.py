"""Structured application error types."""


class RepoLensError(RuntimeError):
    """Base application error with a safe message and machine-readable code."""

    def __init__(
        self,
        message: str,
        error_code: str,
        diagnostics: dict | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.diagnostics = diagnostics or {}

    def to_dict(self) -> dict:
        """Return a serializable error payload."""
        return {
            "error_code": self.error_code,
            "error_message": str(self),
            "diagnostics": self.diagnostics,
        }


class RepositoryCloneError(RepoLensError):
    """Raised when cloning a repository fails."""


class IngestionLimitError(RepoLensError):
    """Raised when repository ingestion exceeds configured limits."""


class VectorStoreError(RepoLensError):
    """Raised when the vector store cannot be accessed safely."""


class RetrievalError(RepoLensError):
    """Raised when retrieval cannot complete successfully."""


class LLMDependencyError(RepoLensError):
    """Raised when LLM dependencies or configuration are unavailable."""


class LLMInvocationError(RepoLensError):
    """Raised when an LLM request fails during invocation."""
