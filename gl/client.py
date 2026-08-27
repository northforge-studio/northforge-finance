from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession

from core.store import (
    CsvStore,
    PostgresStore,
)

from registry import RegistryClient

from gl.manager import GLManager
from gl.models import (
    GLInstruction,
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
    ) -> 'GLClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                'SEGMENT_DEFAULT': Path(segment_default_path),
            },
        )

        return cls(GLRepository(store), registry)


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        segment_default_table: str,
        registry: RegistryClient,
    ) -> 'GLClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                'SEGMENT_DEFAULT': segment_default_table,
            },
        )

        return cls(GLRepository(store), registry)


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
