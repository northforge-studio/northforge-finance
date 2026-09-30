class BreakAnalysisError(RuntimeError):
    """Base exception for Break Analysis runtime failures."""


class ToolTransientError(BreakAnalysisError):
    """Temporary tool dependency failure that may succeed if retried."""
