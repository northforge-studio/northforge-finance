from datetime import date
from pathlib import Path
from uuid import UUID

from pyspark.sql import SparkSession

from core.store import (
    CsvStore,
    PostgresStore,
)
from core.runs import RunIdentity

from registry import RegistryClient

from gl.manager import GLManager
from gl.models import (
    GLImportResult,
    GLInstruction,
    GLInstructionResult,
    GLPosting,
    GLRejection,
    GLSegmentResolution,
    GLSegments,
    InstructionValidation,
    SegmentResolution,
)
from gl.repository import GLRepository


class GLClient:
    def __init__(self, repository: GLRepository, registry: RegistryClient):
        self._repository = repository
        self._registry = registry
        self._manager = GLManager(repository, registry)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        segment_default_path: str | Path,
        registry: RegistryClient,
        posting_path: str | Path | None = None,
        rejection_path: str | Path | None = None,
        interface_trial_balance_path: str | Path | None = None,
    ) -> 'GLClient':
        table_locations = {
            'SEGMENT_DEFAULT': Path(segment_default_path),
        }
        if posting_path is not None:
            table_locations['POSTING'] = Path(posting_path)
        if rejection_path is not None:
            table_locations['REJECTION'] = Path(rejection_path)
        if interface_trial_balance_path is not None:
            table_locations['INTERFACE_TRIAL_BALANCE'] = Path(
                interface_trial_balance_path
            )

        store = CsvStore(
            spark=spark,
            table_locations=table_locations,
        )

        return cls(GLRepository(store, spark), registry)


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        segment_default_table: str,
        registry: RegistryClient,
        posting_table: str = 'gl.posting',
        rejection_table: str = 'gl.rejection',
        interface_trial_balance_table: str = 'interface.trial_balance',
    ) -> 'GLClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                'SEGMENT_DEFAULT': segment_default_table,
                'POSTING': posting_table,
                'REJECTION': rejection_table,
                'INTERFACE_TRIAL_BALANCE': interface_trial_balance_table,
            },
        )

        return cls(GLRepository(store, spark), registry)


    def get_segment_default(
        self,
        segment_type: str,
        *,
        entity_cd: str | None = None,
    ) -> str | None:
        return self._manager.get_segment_default(
            segment_type,
            entity_cd=entity_cd,
        )


    def resolve_segment(
        self,
        segment_type: str,
        segment_value: str | None,
        *,
        business_dt: date,
        entity_cd: str | None = None,
    ) -> SegmentResolution:
        return self._manager.resolve_segment(
            segment_type,
            segment_value,
            business_dt=business_dt,
            entity_cd=entity_cd,
        )


    def resolve_segments(
        self,
        segments: GLSegments,
        *,
        business_dt: date,
    ) -> GLSegmentResolution:
        return self._manager.resolve_segments(
            segments,
            business_dt=business_dt,
        )


    def validate_instruction(
        self,
        instruction: GLInstruction,
    ) -> InstructionValidation:
        return self._manager.validate_instruction(instruction)


    def process_instruction(
        self,
        instruction: GLInstruction,
    ) -> GLInstructionResult:
        return self._manager.process_instruction(instruction)


    def import_instructions(
        self,
        identity: RunIdentity,
        source_producer_run_id: UUID,
    ) -> GLImportResult:
        return self._manager.import_instructions(identity, source_producer_run_id)


    def rollback_execution(self, identity: RunIdentity) -> None:
        self._manager.rollback_execution(identity)


    def get_postings(self, producer_run_id: UUID) -> tuple[GLPosting, ...]:
        return self._manager.get_postings(producer_run_id)


    def get_rejections(self, producer_run_id: UUID) -> tuple[GLRejection, ...]:
        return self._manager.get_rejections(producer_run_id)
