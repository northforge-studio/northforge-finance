from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable

from gl.models import GLSegmentDefaults, GLSegmentType

from break_analysis.models import BreakRecord, BreakPartitionKey


_TRANSFORMABLE_SEGMENTS = (
    GLSegmentType.DEPARTMENT,
    GLSegmentType.BRANCH,
    GLSegmentType.ACCOUNT,
    GLSegmentType.SUB_ACCOUNT,
    GLSegmentType.AFFILIATE,
    GLSegmentType.PRODUCT,
    GLSegmentType.BOOK,
)


@dataclass(frozen=True)
class _PivotCandidate:
    record: BreakRecord
    relaxed_segments: tuple[GLSegmentType, ...]


class BreakCaseBuilder:

    def __init__(
            self,
            segment_defaults: GLSegmentDefaults
    ):
        self._segment_defaults = segment_defaults
    

    def _partition(
        self,
        records: Iterable[BreakRecord],
    ) -> dict[BreakPartitionKey, tuple[BreakRecord, ...]]:
        partitions: dict[BreakPartitionKey, list[BreakRecord]] = defaultdict(list)

        for record in records:
            key = BreakPartitionKey(
                as_of_date=record.as_of_date,
                entity_cd=record.segments.entity_cd,
                source_cd=record.segments.source_cd,
                accounted_currency=record.accounted_currency,
            )
            partitions[key].append(record)

        return {
            key: tuple(records)
            for key, records in partitions.items()
        }


    def _resolve_applicable_defaults(
            self,
            partition_key: BreakPartitionKey
    ) -> dict[GLSegmentType, str]:
        defaults: dict[GLSegmentType, str] = {}

        for segment_type in _TRANSFORMABLE_SEGMENTS:
            value = self._segment_defaults.resolve(
                segment_type=segment_type,
                entity_cd=partition_key.entity_cd,
            )

            if value is not None:
                defaults[segment_type] = value

        return defaults


    def _find_pivots(
        self,
        partition_key: BreakPartitionKey,
        records: Iterable[BreakRecord]
    ) -> tuple[_PivotCandidate, ...]:
        applicable_defaults = self._resolve_applicable_defaults(
            partition_key=partition_key,
        )

        pivots: list[BreakRecord] = []

        for record in records:
            relaxed_segments = tuple(
                segment_type
                for segment_type, default_value in applicable_defaults.items()
                if getattr(
                    record.segments,
                    segment_type.field_name
                ) == default_value
            )

            if relaxed_segments:
                pivots.append(
                    _PivotCandidate(
                        record=record,
                        relaxed_segments=relaxed_segments
                    )
                )

        return tuple(pivots)
