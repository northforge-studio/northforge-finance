from datetime import date
from dataclasses import dataclass

from pydantic import BaseModel

from registry import RegistryClient
from registry.models import GLSegmentType


class ValidateSegmentInput(BaseModel):
    segment_type: GLSegmentType
    segment_value: str
    business_dt: date


@dataclass(frozen=True)
class SegmentValidationResult:
    segment_type: GLSegmentType
    segment_value: str
    is_valid: bool


@dataclass(frozen=True)
class SegmentDetailsResult:
    segment_type: GLSegmentType
    segment_value: str
    exists: bool
    status: str | None


class RegistryTools:
    def __init__(
        self,
        registry_client: RegistryClient
    ):
        self._registry = registry_client


    def validate_segment(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date
    ) -> SegmentValidationResult:
        is_valid = self._registry.validate_segment(
            segment_type,
            business_dt,
            segment_value
        )

        return SegmentValidationResult(
            segment_type=segment_type,
            segment_value=segment_value,
            is_valid=is_valid
        )


    def get_segment_details(
        self,
        segment_type: GLSegmentType,
        segment_value: str,
        business_dt: date,
    ) -> SegmentDetailsResult:
        df = self._registry.get_segment_details(
            segment=segment_type,
            business_dt=business_dt,
            segment_cd=segment_value,
        )

        row = df.first()

        if row is None:
            return SegmentDetailsResult(
                segment_type=segment_type,
                segment_value=segment_value,
                exists=False,
                status=None,
            )

        return SegmentDetailsResult(
            segment_type=segment_type,
            segment_value=segment_value,
            exists=True,
            status=row['STATUS'],
        )
