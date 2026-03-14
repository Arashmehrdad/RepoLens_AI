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


class RepoStateError(RepoLensError):
    """Raised when a repo state cannot be resolved or loaded safely."""


class VectorStoreError(RepoLensError):
    """Raised when the vector store cannot be accessed safely."""


class RetrievalError(RepoLensError):
    """Raised when retrieval cannot complete successfully."""


class LLMDependencyError(RepoLensError):
    """Raised when LLM dependencies or configuration are unavailable."""


class LLMInvocationError(RepoLensError):
    """Raised when an LLM request fails during invocation."""


class ComparisonError(RepoLensError):
    """Raised when repo-to-repo comparison cannot complete safely."""


class RegressionError(RepoLensError):
    """Raised when eval regression data cannot be loaded safely."""


class ReportGenerationError(RepoLensError):
    """Raised when an exportable review report cannot be generated."""
