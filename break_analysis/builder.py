from collections import defaultdict
from collections.abc import Iterable

from break_analysis.models import BreakRecord, BreakPartitionKey


class BreakCaseBuilder:

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
