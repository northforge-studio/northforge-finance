from datetime import date
from dataclasses import dataclass

from pydantic import BaseModel

from registry import RegistryClient, SegmentType


class ValidateSegmentInput(BaseModel):
    segment_type: SegmentType
    segment_value: str
    business_dt: date


@dataclass(frozen=True)
class SegmentValidationResult:
    segment_type: str
    segment_value: str
    is_valid: bool


class RegistryTools:
    def __init__(
        self, 
        registry_client: RegistryClient
    ):
        self._registry = registry_client


    def validate_segment(
        self,
        segment_type: SegmentType,
        segment_value: str,
        business_dt: date,
    ) -> SegmentValidationResult:
        is_valid = self._registry.validate_segment(
            segment_type,
            business_dt,
            segment_value,
        )

        return SegmentValidationResult(
            segment_type=segment_type,
            segment_value=segment_value,
            is_valid=is_valid,
        )
