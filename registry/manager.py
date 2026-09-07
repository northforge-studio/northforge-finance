from datetime import date

from pyspark.sql import DataFrame

from registry.models import GLSegmentType
from registry.repository import RegistryRepository


class RegistryManager:
    def __init__(self, repository: RegistryRepository):
        self._repository = repository


    def validate_segment(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> bool:
        records = self._repository.get_segment(segment, business_dt, segment_cd)

        return records.count() > 0


    def get_segment_details(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> DataFrame:
        if not self.validate_segment(segment, business_dt, segment_cd):
            raise KeyError(
                f'Segment not found for '
                f'SEGMENT={segment!r}, '
                f'BUSINESS_DT={business_dt!r}, '
                f'SEGMENT_CD={segment_cd!r}'
            )

        return self._repository.get_segment(segment, business_dt, segment_cd)
