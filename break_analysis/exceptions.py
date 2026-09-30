class BreakAnalysisError(RuntimeError):
    """Base exception for Break Analysis runtime failures."""


class ToolTransientError(BreakAnalysisError):
    """Temporary tool dependency failure that may succeed if retried."""


class ModelTransientError(RuntimeError):
    """Temporary model/provider failure that may succeed if retried."""
