from datetime import date
from decimal import Decimal
from uuid import UUID

from break_analysis.models import (
    BreakAnalysisStatus,
    BreakCase,
    BreakRecord,
    BreakTopology,
)
from break_analysis.tools.registry import SegmentValidationResult
from evals.models import EvalExpectation, EvalScenario, ToolFixture
from gl.models import GLSegments
from registry.models import GLSegmentType


def interface_only_no_supported_cause() -> EvalScenario:
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
        interface_balance=Decimal('4700.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('4700.00'),
    )

    break_case = BreakCase(
        case_id=UUID('11111111-1111-1111-1111-111111111111'),
        topology=BreakTopology.INTERFACE_ONLY,
        investigation_records=(investigation_record,),
        pivot=None,
        evidence=None,
    )

    scenario = EvalScenario(
        name='interface_only_no_supported_cause',
        description=(
            'INTERFACE_ONLY record whose GL segments are all nonblank and '
            'valid in Registry; no supported root cause is established.'
        ),
        break_case=break_case,
        tool_fixtures=(
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.ENTITY,
                    'segment_value': '1000',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.ENTITY,
                    segment_value='1000',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.BRANCH,
                    'segment_value': '0100',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.BRANCH,
                    segment_value='0100',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.DEPARTMENT,
                    'segment_value': '4200',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.DEPARTMENT,
                    segment_value='4200',
                    is_valid=True,
                ),
            ),
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
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.SUB_ACCOUNT,
                    'segment_value': '0000',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.SUB_ACCOUNT,
                    segment_value='0000',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.AFFILIATE,
                    'segment_value': '0000',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.AFFILIATE,
                    segment_value='0000',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.PRODUCT,
                    'segment_value': 'LOAN',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.PRODUCT,
                    segment_value='LOAN',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.BOOK,
                    'segment_value': 'ACTUAL',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.BOOK,
                    segment_value='ACTUAL',
                    is_valid=True,
                ),
            ),
            ToolFixture(
                tool_name='validate_segment',
                args={
                    'segment_type': GLSegmentType.SOURCE,
                    'segment_value': 'CORE',
                    'business_dt': investigation_record.as_of_date,
                },
                result=SegmentValidationResult(
                    segment_type=GLSegmentType.SOURCE,
                    segment_value='CORE',
                    is_valid=True,
                ),
            ),
        ),
        expected=EvalExpectation(
            status=BreakAnalysisStatus.UNEXPLAINED,
            findings=(),
            required_tools=('validate_segment',),
            forbidden_tools=(
                'get_segment_details',
                'investigate_resolution',
            ),
        ),
    )

    return scenario
