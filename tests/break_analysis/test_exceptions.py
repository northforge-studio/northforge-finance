import pytest

from break_analysis.exceptions import (
    BreakAnalysisError,
    InvalidToolArgumentsError,
    MaxToolRoundsError,
    ModelTransientError,
    StructuredOutputError,
    ToolExecutionError,
    ToolTransientError,
    UnknownToolError,
)

# -- hierarchy -------------------------------------------------------------


@pytest.mark.parametrize(
    'error_type',
    [
        ModelTransientError,
        MaxToolRoundsError,
        UnknownToolError,
        InvalidToolArgumentsError,
        ToolExecutionError,
        ToolTransientError,
        StructuredOutputError,
    ],
)
def test_error_type_is_break_analysis_error(error_type):
    assert issubclass(error_type, BreakAnalysisError)
    assert issubclass(error_type, RuntimeError)


def test_tool_transient_error_is_tool_execution_error():
    assert issubclass(ToolTransientError, ToolExecutionError)
