from uuid import UUID, uuid4
from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable

from gl.models import GLSegmentDefaults
from registry.models import GLSegmentType

from break_analysis.models import (
    BreakCase,
    BreakRecord, 
    BreakTopology,
    BreakCaseEvidence,
    BreakPartitionKey,
)


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


@dataclass(frozen=True)
class _BreakCaseCandidate:
    records: tuple[BreakRecord, ...]
    topology: BreakTopology
    relaxed_segments: tuple[GLSegmentType, ...]


@dataclass(frozen=True)
class _ResolvedCandidate:
    records: tuple[BreakRecord, ...]
    topology: BreakTopology
    relaxed_segments: tuple[GLSegmentType, ...] | None


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

        pivots: list[_PivotCandidate] = []

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


    def _find_neighborhood(
        self,
        pivot: _PivotCandidate,
        records: Iterable[BreakRecord],
        pivot_ids: frozenset[UUID],
    ) -> tuple[BreakRecord, ...]:
        effective_anchors = tuple(
            segment_type
            for segment_type in _TRANSFORMABLE_SEGMENTS
            if segment_type not in pivot.relaxed_segments
        )

        pivot_signature = tuple(
            getattr(pivot.record.segments, segment_type.field_name)
            for segment_type in effective_anchors
        )

        neighborhood = tuple(
            record
            for record in records
            if (
                record.recon_result_id == pivot.record.recon_result_id
                or record.recon_result_id not in pivot_ids
            )
            and tuple(
                getattr(
                    record.segments,
                    segment_type.field_name,
                )
                for segment_type in effective_anchors
            ) == pivot_signature
        )

        return neighborhood


    def _is_closed(
        self,
        records: Iterable[BreakRecord],
    ) -> bool:
        return sum(
            record.difference_amount
            for record in records
        ) == 0


    def _build_candidate(
        self,
        pivot: _PivotCandidate,
        records: Iterable[BreakRecord],
        pivot_ids: frozenset[UUID],
    ) -> _BreakCaseCandidate | None:
        neighborhood = self._find_neighborhood(
            pivot,
            records,
            pivot_ids,
        )

        if len(neighborhood) < 2:
            return None

        if not self._is_closed(neighborhood):
            return None

        topology = (
            BreakTopology.ONE_TO_ONE
            if len(neighborhood) == 2
            else BreakTopology.MANY_TO_ONE
        )

        return _BreakCaseCandidate(
            records=neighborhood,
            topology=topology,
            relaxed_segments=pivot.relaxed_segments,
        )


    def _find_candidates(
        self,
        partition_key: BreakPartitionKey,
        records: tuple[BreakRecord, ...],
    ) -> tuple[_BreakCaseCandidate, ...]:
        pivots = self._find_pivots(
            partition_key,
            records,
        )

        pivot_ids = frozenset(
            pivot.record.recon_result_id
            for pivot in pivots
        )

        candidates: list[_BreakCaseCandidate] = []

        for pivot in pivots:
            candidate = self._build_candidate(
                pivot,
                records,
                pivot_ids,
            )

            if candidate is not None:
                candidates.append(candidate)

        return tuple(candidates)


    def _deduplicate_candidates(
        self,
        candidates: Iterable[_BreakCaseCandidate],
    ) -> tuple[_BreakCaseCandidate, ...]:
        seen: set[
            tuple[
                frozenset[UUID],
                BreakTopology,
                tuple[GLSegmentType, ...],
            ]
        ] = set()

        deduplicated: list[_BreakCaseCandidate] = []

        for candidate in candidates:
            key = (
                frozenset(
                    record.recon_result_id
                    for record in candidate.records
                ),
                candidate.topology,
                candidate.relaxed_segments,
            )

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(candidate)

        return tuple(deduplicated)


    def _resolve_candidates(
        self,
        candidates: Iterable[_BreakCaseCandidate],
    ) -> tuple[_ResolvedCandidate, ...]:
        remaining = list(candidates)
        resolved: list[_ResolvedCandidate] = []

        while remaining:
            current = remaining.pop(0)

            component = [current]
            component_ids = {
                record.recon_result_id
                for record in current.records
            }

            changed = True

            while changed:
                changed = False

                for candidate in remaining[:]:
                    candidate_ids = {
                        record.recon_result_id
                        for record in candidate.records
                    }

                    if component_ids & candidate_ids:
                        component.append(candidate)
                        component_ids.update(candidate_ids)
                        remaining.remove(candidate)
                        changed = True

            if len(component) == 1:
                resolved.append(
                    _ResolvedCandidate(
                        records=current.records,
                        topology=current.topology,
                        relaxed_segments=current.relaxed_segments,
                    )
                )
                continue

            records_by_id = {
                record.recon_result_id: record
                for candidate in component
                for record in candidate.records
            }

            resolved.append(
                _ResolvedCandidate(
                    records=tuple(records_by_id.values()),
                    topology=BreakTopology.AMBIGUOUS,
                    relaxed_segments=None,
                )
            )

        return tuple(resolved)


    def _to_break_cases(
        self,
        candidates: Iterable[_ResolvedCandidate],
    ) -> tuple[BreakCase, ...]:
        cases: list[BreakCase] = []

        for candidate in candidates:
            evidence = (
                BreakCaseEvidence(
                    relaxed_segments=candidate.relaxed_segments,
                )
                if candidate.relaxed_segments is not None
                else None
            )

            cases.append(
                BreakCase(
                    case_id=uuid4(),
                    topology=candidate.topology,
                    records=candidate.records,
                    evidence=evidence,
                )
            )

        return tuple(cases)
