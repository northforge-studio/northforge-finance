from pathlib import Path

from pyspark.sql import SparkSession

from core.store import (
    CsvStore,
    PostgresStore,
)

from gl.manager import GLManager
from gl.repository import GLRepository


class GLClient:
    def __init__(self, repository: GLRepository):
        self._repository = repository
        self._manager = GLManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        segment_default_path: str | Path,
    ) -> 'GLClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                'SEGMENT_DEFAULT': Path(segment_default_path),
            },
        )

        return cls(GLRepository(store))


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        segment_default_table: str,
    ) -> 'GLClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                'SEGMENT_DEFAULT': segment_default_table,
            },
        )

        return cls(GLRepository(store))


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
