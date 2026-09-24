from uuid import UUID
from datetime import date

from registry.models import GLSegmentType

from evals.fixtures import ToolFixtureStore


class FakeRegistryTools:
    def __init__(self, fixture_store: ToolFixtureStore):
        self._fixtures = fixture_store


    def validate_segment(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date,
    ):
        return self._fixtures.get_result(
            'validate_segment',
            {
                'segment_type': segment_type,
                'segment_value': segment_value,
                'business_dt': business_dt,
            },
        )


    def get_segment_details(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date,
    ):
        return self._fixtures.get_result(
            'get_segment_details',
            {
                'segment_type': segment_type,
                'segment_value': segment_value,
                'business_dt': business_dt,
            },
        )


class FakeAtlasTools:
    def __init__(self, fixture_store: ToolFixtureStore):
        self._fixtures = fixture_store


    def investigate_resolution(
        self,
        workflow_run_id: UUID,
        recon_result_id: UUID,
        segment_type: GLSegmentType,
    ):
        return self._fixtures.get_result(
            'investigate_resolution',
            {
                'workflow_run_id': workflow_run_id,
                'recon_result_id': recon_result_id,
                'segment_type': segment_type,
            },
        )
