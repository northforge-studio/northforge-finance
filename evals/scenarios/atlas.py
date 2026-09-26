from uuid import UUID
from datetime import date
from decimal import Decimal

from gl.models import GLSegments

from atlas.models import MappingResolutionEvidence

from registry.models import GLSegmentType

from break_analysis.models import (
    BreakCase,
    RootCause,
    BreakRecord,
    BreakTopology,
    BreakCaseEvidence,
    BreakAnalysisStatus,
    AtlasInputResolution,
    AtlasResolutionEvidence,
    FoundryMappingInputValues
)

from evals.models import (
    ToolFixture,
    EvalScenario,
    EvalExpectation,
    ExpectedFinding
)


def atlas_unresolved_account() -> EvalScenario:
    investigation_record = BreakRecord(
        recon_result_id=UUID('22222222-2222-2222-2222-222222222222'),
        workflow_run_id=UUID('33333333-3333-3333-3333-333333333333'),
        as_of_date=date(2026, 3, 31),
        segments=GLSegments(
            entity_cd='1000',
            branch_cd='0100',
            dept_cd='4200',
            gl_account='',
            sub_account='0000',
            affiliate_cd='0000',
            product_cd='LOAN',
            book_cd='ACTUAL',
            source_cd='CORE',
        ),
        accounted_currency='USD',
        interface_balance=Decimal('12500.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('12500.00'),
    )

    pivot = BreakRecord(
        recon_result_id=UUID('44444444-4444-4444-4444-444444444444'),
        workflow_run_id=UUID('33333333-3333-3333-3333-333333333333'),
        as_of_date=date(2026, 3, 31),
        segments=GLSegments(
            entity_cd='1000',
            branch_cd='0100',
            dept_cd='4200',
            gl_account='199999',
            sub_account='0000',
            affiliate_cd='0000',
            product_cd='LOAN',
            book_cd='ACTUAL',
            source_cd='CORE',
        ),
        accounted_currency='USD',
        interface_balance=Decimal('0.00'),
        gl_balance=Decimal('12500.00'),
        difference_amount=Decimal('-12500.00'),
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

    foundry_input_values = {
        'SRC_APP_CD': 'CORE',
        'SRC_ENTITY_CD': '1000',
        'DATACLASS': 'BAL',
        'COA_RULE_ID': 'LN01',
        'SRC_ACCOUNT_ID': 'LN-4410',
    }

    scenario = EvalScenario(
        name='atlas_unresolved_account',
        description=(
            'GL_ACCOUNT is blank because no active Atlas mapping '
            'resolved the Foundry input values.'
        ),
        break_case=break_case,
        tool_fixtures=(
            ToolFixture(
                tool_name='investigate_resolution',
                args={
                    'workflow_run_id': investigation_record.workflow_run_id,
                    'recon_result_id': investigation_record.recon_result_id,
                    'segment_type': GLSegmentType.ACCOUNT,
                },
                result=AtlasResolutionEvidence(
                    recon_result_id=investigation_record.recon_result_id,
                    segment_type=GLSegmentType.ACCOUNT,
                    mapping_name='ACCOUNT_TB_MAPPING',
                    input_resolutions=(
                        AtlasInputResolution(
                            foundry_inputs=FoundryMappingInputValues(
                                values=foundry_input_values,
                                source_record_count=3,
                            ),
                            resolution=MappingResolutionEvidence(
                                mapping_name='ACCOUNT_TB_MAPPING',
                                input_values=foundry_input_values,
                                candidates=(),
                                active_candidate_found=False,
                                resolved=False,
                                mapping_output=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
        expected=EvalExpectation(
            status=BreakAnalysisStatus.EXPLAINED,
            findings=(
                ExpectedFinding(
                    root_cause=RootCause.ATLAS_UNRESOLVED_SEGMENT,
                    recon_result_id=(
                        investigation_record.recon_result_id
                    ),
                    segment_type=GLSegmentType.ACCOUNT,
                    segment_value='',
                ),
            ),
            required_tools=(
                'investigate_resolution',
            ),
            forbidden_tools=(
                'validate_segment',
                'get_segment_details',
            ),
        ),
    )

    return scenario
