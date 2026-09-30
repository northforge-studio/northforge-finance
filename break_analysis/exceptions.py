class BreakAnalysisError(RuntimeError):
    """Base exception for Break Analysis runtime failures."""


class ModelTransientError(BreakAnalysisError):
    """Temporary model/provider failure that may succeed if retried."""


class MaxToolRoundsError(BreakAnalysisError):
    """The agent requested more tool rounds than allowed."""


class UnknownToolError(BreakAnalysisError):
    """The agent requested a tool that is not registered."""


class InvalidToolArgumentsError(BreakAnalysisError):
    """The agent's tool call arguments failed the tool's args schema."""


class ToolExecutionError(BreakAnalysisError):
    """A tool failed while executing."""


class ToolTransientError(ToolExecutionError):
    """Temporary tool dependency failure that may succeed if retried."""


class StructuredOutputError(BreakAnalysisError):
    """The conclusion could not be parsed into BreakAnalysisConclusion."""
