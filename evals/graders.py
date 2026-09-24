from collections import Counter

from break_analysis.models import BreakAnalysisResult

from evals.models import (
    EvalScenario,
    EvalGrade,
    ToolCallRecord,
)


def grade_scenario(
    scenario: EvalScenario,
    result: BreakAnalysisResult,
    calls: tuple[ToolCallRecord, ...],
) -> EvalGrade:
    failures: list[str] = []

    expected = scenario.expected

    # Status
    if result.status != expected.status:
        failures.append(
            f'Expected status {expected.status}, got {result.status}.'
        )

    # Findings — compare semantic identity, ignore explanation and ordering.
    expected_findings = Counter(
        (
            finding.root_cause,
            finding.recon_result_id,
            finding.segment_type,
            finding.segment_value,
        )
        for finding in expected.findings
    )

    actual_findings = Counter(
        (
            finding.root_cause,
            finding.recon_result_id,
            finding.segment_type,
            finding.segment_value,
        )
        for finding in result.findings
    )

    missing_findings = expected_findings - actual_findings
    extra_findings = actual_findings - expected_findings

    for finding, count in missing_findings.items():
        failures.append(
            f'Missing expected finding ({count}x): {finding}.'
        )

    for finding, count in extra_findings.items():
        failures.append(
            f'Unexpected finding ({count}x): {finding}.'
        )

    # Tool behavior
    called_tools = [call.tool_name for call in calls]

    for tool_name in expected.required_tools:
        if tool_name not in called_tools:
            failures.append(
                f'Required tool was not called: {tool_name}.'
            )

    for tool_name in expected.forbidden_tools:
        if tool_name in called_tools:
            failures.append(
                f'Forbidden tool was called: {tool_name}.'
            )

    return EvalGrade(
        passed=not failures,
        failures=tuple(failures),
    )
