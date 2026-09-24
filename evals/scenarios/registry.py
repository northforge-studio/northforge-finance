from uuid import UUID
from datetime import date
from decimal import Decimal

from gl.models import GLSegments

from registry.models import GLSegmentType

from break_analysis.models import (
    BreakCase,
    RootCause,
    BreakRecord,
    BreakTopology,
    BreakCaseEvidence,
    BreakAnalysisStatus
)
from break_analysis.tools.registry import (
    SegmentValidationResult,
    SegmentDetailsResult
)

from evals.models import (
    ToolFixture,
    EvalScenario,
    EvalExpectation,
    ExpectedFinding
)


def registry_inactive_account() -> EvalScenario:
    investigation_record = BreakRecord(
        recon_result_id=UUID('22222222-2222-2222-2222-222222222222'),
        workflow_run_id=UUID('33333333-3333-3333-3333-333333333333'),
        as_of_date=date(2026, 3, 31),
        segments=GLSegments(
            entity_cd='1000',
            branch_cd='0100',
            dept_cd='4200',
            gl_account='210000',
            sub_account='0000',
            affiliate_cd='0000',
            product_cd='LOAN',
            book_cd='ACTUAL',
            source_cd='CORE',
        ),
        accounted_currency='USD',
        interface_balance=Decimal('15000.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('15000.00'),
    )

    pivot = BreakRecord(
        recon_result_id=UUID('44444444-4444-4444-4444-444444444444'),
        workflow_run_id=UUID('33333333-3333-3333-3333-333333333333'),
        as_of_date=date(2026, 3, 31),
        segments=GLSegments(
            entity_cd='1000',
            branch_cd='0100',
            dept_cd='4200',
            gl_account='110000',
            sub_account='0000',
            affiliate_cd='0000',
            product_cd='LOAN',
            book_cd='ACTUAL',
            source_cd='CORE',
        ),
        accounted_currency='USD',
        interface_balance=Decimal('0.00'),
        gl_balance=Decimal('15000.00'),
        difference_amount=Decimal('-15000.00'),
    )

    break_case = BreakCase(
        case_id=UUID('11111111-1111-1111-1111-111111111111'),
        topology=BreakTopology.ONE_TO_ONE,
        investigation_records=(
            investigation_record,
        ),
        pivot=pivot,
        evidence=BreakCaseEvidence(
            relaxed_segments=(GLSegmentType.ACCOUNT,),
        ),
    )

    scenario = EvalScenario(
        name='registry_inactive_account',
        description='GL_ACCOUNT exists in Registry but is inactive.',
        break_case=break_case,
        tool_fixtures=(
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.ACCOUNT,
                    'segment_value': '210000',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.ACCOUNT,
                    segment_value='210000',
                    is_valid=False,
                ),
            ),
            ToolFixture(
                tool_name='get_segment_details',
                args={
                    'segment_type': GLSegmentType.ACCOUNT,
                    'segment_value': '210000',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentDetailsResult(
                    segment_type=GLSegmentType.ACCOUNT,
                    segment_value='210000',
                    exists=True,
                    status='I',
                ),
            ),
        ),
        expected=EvalExpectation(
            status=BreakAnalysisStatus.EXPLAINED,
            findings=(
                ExpectedFinding(
                    root_cause=RootCause.REGISTRY_INVALID_SEGMENT,
                    recon_result_id=(
                        investigation_record.recon_result_id
                    ),
                    segment_type=GLSegmentType.ACCOUNT,
                    segment_value='210000',
                ),
            ),
            required_tools=(
                'validate_segment',
                'get_segment_details',
            ),
            forbidden_tools=(
                'investigate_resolution',
            ),
        ),
    )

    return scenario
