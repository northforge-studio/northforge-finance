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
        records = self._repository.get_active_segment(segment, business_dt, segment_cd)

        return records.count() > 0


    def get_segment_details(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> DataFrame:
        return self._repository.get_segment_details(segment, business_dt, segment_cd)
