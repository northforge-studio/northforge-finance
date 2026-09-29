from datetime import date
from typing import TypeVar
from uuid import UUID

from break_analysis.services.atlas import AtlasResolutionEvidence
from break_analysis.tools.registry import SegmentDetailsResult, SegmentValidationResult
from evals.fixtures import ToolFixtureStore
from registry.models import GLSegmentType

T = TypeVar('T')


def _expect_result(result: object, result_type: type[T]) -> T:
    if not isinstance(result, result_type):
        raise TypeError(
            f'Expected a {result_type.__name__} fixture result, '
            f'got {type(result).__name__}.'
        )

    return result


class FakeRegistryTools:
    """Implements RegistryToolsProtocol from recorded tool fixtures."""

    def __init__(self, fixture_store: ToolFixtureStore):
        self._fixtures = fixture_store

    def validate_segment(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date,
    ) -> SegmentValidationResult:
        result = self._fixtures.get_result(
            'validate_segment',
            {
                'segment_type': segment_type,
                'segment_value': segment_value,
                'business_dt': business_dt,
            },
        )

        return _expect_result(result, SegmentValidationResult)

    def get_segment_details(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date,
    ) -> SegmentDetailsResult:
        result = self._fixtures.get_result(
            'get_segment_details',
            {
                'segment_type': segment_type,
                'segment_value': segment_value,
                'business_dt': business_dt,
            },
        )

        return _expect_result(result, SegmentDetailsResult)


class FakeAtlasTools:
    """Implements AtlasToolsProtocol from recorded tool fixtures."""

    def __init__(self, fixture_store: ToolFixtureStore):
        self._fixtures = fixture_store

    def investigate_resolution(
        self,
        workflow_run_id: UUID,
        recon_result_id: UUID,
        segment_type: GLSegmentType,
    ) -> AtlasResolutionEvidence:
        result = self._fixtures.get_result(
            'investigate_resolution',
            {
                'workflow_run_id': workflow_run_id,
                'recon_result_id': recon_result_id,
                'segment_type': segment_type,
            },
        )

        return _expect_result(result, AtlasResolutionEvidence)
