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
    BreakPartitionKey
)


_TRANSFORMABLE_SEGMENTS = (
    GLSegmentType.DEPARTMENT,
    GLSegmentType.BRANCH,
    GLSegmentType.ACCOUNT,
    GLSegmentType.SUB_ACCOUNT,
    GLSegmentType.AFFILIATE,
    GLSegmentType.PRODUCT,
    GLSegmentType.BOOK
)


@dataclass(frozen=True)
class _PivotCandidate:
    record: BreakRecord
    relaxed_segments: tuple[GLSegmentType, ...]


@dataclass(frozen=True)
class _BreakCaseCandidate:
    topology: BreakTopology
    pivot: BreakRecord
    investigation_records: tuple[BreakRecord, ...]
    relaxed_segments: tuple[GLSegmentType, ...]


    @property
    def all_records(self) -> tuple[BreakRecord, ...]:
        return (
            self.pivot,
            *self.investigation_records
        )


@dataclass(frozen=True)
class _ResolvedCandidate:
    topology: BreakTopology
    pivot: BreakRecord | None
    investigation_records: tuple[BreakRecord, ...]
    relaxed_segments: tuple[GLSegmentType, ...] | None


    @property
    def all_records(self) -> tuple[BreakRecord, ...]:
        if self.pivot is None:
            return self.investigation_records

        return (
            self.pivot,
            *self.investigation_records
        )


class BreakCaseBuilder:

    def __init__(
        self,
        segment_defaults: GLSegmentDefaults
    ):
        self._segment_defaults = segment_defaults


    def build(
        self,
        records: Iterable[BreakRecord]
    ) -> tuple[BreakCase, ...]:
        records = tuple(records)

        cases: list[BreakCase] = []

        for partition_key, partition_records in self._partition(records).items():
            candidates = self._find_candidates(
                partition_key,
                partition_records
            )

            candidates = self._deduplicate_candidates(candidates)

            resolved = self._resolve_candidates(candidates)

            candidate_cases = self._to_break_cases(resolved)

            cases.extend(candidate_cases)

            consumed_ids = {
                record.recon_result_id
                for case in candidate_cases
                for record in case.all_records
            }

            leftovers = tuple(
                record
                for record in partition_records
                if record.recon_result_id not in consumed_ids
            )

            cases.extend(
                self._classify_leftovers(leftovers)
            )

        return tuple(cases)


    def _partition(
        self,
        records: Iterable[BreakRecord]
    ) -> dict[BreakPartitionKey, tuple[BreakRecord, ...]]:
        partitions: dict[BreakPartitionKey, list[BreakRecord]] = defaultdict(list)

        for record in records:
            key = BreakPartitionKey(
                as_of_date=record.as_of_date,
                entity_cd=record.segments.entity_cd,
                source_cd=record.segments.source_cd,
                accounted_currency=record.accounted_currency
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
                entity_cd=partition_key.entity_cd
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
            partition_key=partition_key
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
        pivot_ids: frozenset[UUID]
    ) -> tuple[BreakRecord, ...]:
        effective_anchors = tuple(
            segment_type
            for segment_type in _TRANSFORMABLE_SEGMENTS
            if segment_type not in pivot.relaxed_segments
        )

        pivot_signature = tuple(
            getattr(
                pivot.record.segments,
                segment_type.field_name
            )
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
                    segment_type.field_name
                )
                for segment_type in effective_anchors
            ) == pivot_signature
        )

        return neighborhood


    def _is_closed(
        self,
        records: Iterable[BreakRecord]
    ) -> bool:
        return sum(
            record.difference_amount
            for record in records
        ) == 0


    def _build_candidate(
        self,
        pivot: _PivotCandidate,
        records: Iterable[BreakRecord],
        pivot_ids: frozenset[UUID]
    ) -> _BreakCaseCandidate | None:
        neighborhood = self._find_neighborhood(
            pivot,
            records,
            pivot_ids
        )

        if len(neighborhood) < 2:
            return None

        if not self._is_closed(neighborhood):
            return None

        investigation_records = tuple(
            record
            for record in neighborhood
            if record.recon_result_id
            != pivot.record.recon_result_id
        )

        topology = (
            BreakTopology.ONE_TO_ONE
            if len(investigation_records) == 1
            else BreakTopology.MANY_TO_ONE
        )

        return _BreakCaseCandidate(
            topology=topology,
            pivot=pivot.record,
            investigation_records=investigation_records,
            relaxed_segments=pivot.relaxed_segments
        )


    def _find_candidates(
        self,
        partition_key: BreakPartitionKey,
        records: tuple[BreakRecord, ...]
    ) -> tuple[_BreakCaseCandidate, ...]:
        pivots = self._find_pivots(
            partition_key,
            records
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
                pivot_ids
            )

            if candidate is not None:
                candidates.append(candidate)

        return tuple(candidates)


    def _deduplicate_candidates(
        self,
        candidates: Iterable[_BreakCaseCandidate]
    ) -> tuple[_BreakCaseCandidate, ...]:
        seen: set[
            tuple[
                UUID,
                frozenset[UUID],
                BreakTopology,
                tuple[GLSegmentType, ...]
            ]
        ] = set()

        deduplicated: list[_BreakCaseCandidate] = []

        for candidate in candidates:
            key = (
                candidate.topology,
                candidate.pivot.recon_result_id,
                frozenset(
                    record.recon_result_id
                    for record in candidate.investigation_records
                ),
                candidate.relaxed_segments
            )

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(candidate)

        return tuple(deduplicated)


    def _resolve_candidates(
        self,
        candidates: Iterable[_BreakCaseCandidate]
    ) -> tuple[_ResolvedCandidate, ...]:
        remaining = list(candidates)
        resolved: list[_ResolvedCandidate] = []

        while remaining:
            current = remaining.pop(0)

            component = [current]
            component_ids = {
                record.recon_result_id
                for record in current.all_records
            }

            changed = True

            while changed:
                changed = False

                for candidate in remaining[:]:
                    candidate_ids = {
                        record.recon_result_id
                        for record in candidate.all_records
                    }

                    if component_ids & candidate_ids:
                        component.append(candidate)
                        component_ids.update(candidate_ids)
                        remaining.remove(candidate)
                        changed = True

            if len(component) == 1:
                resolved.append(
                    _ResolvedCandidate(
                        topology=current.topology,
                        pivot=current.pivot,
                        investigation_records=(
                            current.investigation_records
                        ),
                        relaxed_segments=current.relaxed_segments
                    )
                )

                continue

            records_by_id = {
                record.recon_result_id: record
                for candidate in component
                for record in candidate.all_records
            }

            resolved.append(
                _ResolvedCandidate(
                    pivot=None,
                    investigation_records=tuple(
                        records_by_id.values()
                    ),
                    topology=BreakTopology.AMBIGUOUS,
                    relaxed_segments=None
                )
            )

        return tuple(resolved)


    def _to_break_cases(
        self,
        candidates: Iterable[_ResolvedCandidate]
    ) -> tuple[BreakCase, ...]:
        cases: list[BreakCase] = []

        for candidate in candidates:
            evidence = (
                BreakCaseEvidence(
                    relaxed_segments=candidate.relaxed_segments
                )
                if candidate.relaxed_segments is not None
                else None
            )

            cases.append(
                BreakCase(
                    case_id=uuid4(),
                    topology=candidate.topology,
                    pivot=candidate.pivot,
                    investigation_records=(
                        candidate.investigation_records
                    ),
                    evidence=evidence
                )
            )

        return tuple(cases)


    def _classify_leftovers(
        self,
        records: Iterable[BreakRecord]
    ) -> tuple[BreakCase, ...]:
        cases: list[BreakCase] = []

        for record in records:
            if record.interface_balance != 0 and record.gl_balance == 0:
                topology = BreakTopology.INTERFACE_ONLY

            elif record.interface_balance == 0 and record.gl_balance != 0:
                topology = BreakTopology.GL_ONLY

            else:
                topology = BreakTopology.UNMATCHED

            cases.append(
                BreakCase(
                    case_id=uuid4(),
                    topology=topology,
                    pivot=None,
                    investigation_records=(record,),
                    evidence=None
                )
            )

        return tuple(cases)
