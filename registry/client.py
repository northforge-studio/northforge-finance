from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import (
    CsvStore,
    PostgresStore
)

from registry.models import GLSegmentType
from registry.manager import RegistryManager
from registry.repository import RegistryRepository


class RegistryClient:
    def __init__(self, repository: RegistryRepository):
        self._repository = repository
        self._manager = RegistryManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        entity_path: str | Path,
        department_path: str | Path,
        branch_path: str | Path,
        account_path: str | Path,
        sub_account_path: str | Path,
        affiliate_path: str | Path,
        product_path: str | Path,
        book_path: str | Path,
        source_path: str | Path,
    ) -> 'RegistryClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                GLSegmentType.ENTITY: Path(entity_path),
                GLSegmentType.DEPARTMENT: Path(department_path),
                GLSegmentType.BRANCH: Path(branch_path),
                GLSegmentType.ACCOUNT: Path(account_path),
                GLSegmentType.SUB_ACCOUNT: Path(sub_account_path),
                GLSegmentType.AFFILIATE: Path(affiliate_path),
                GLSegmentType.PRODUCT: Path(product_path),
                GLSegmentType.BOOK: Path(book_path),
                GLSegmentType.SOURCE: Path(source_path),
            },
        )

        return cls(RegistryRepository(store))


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        entity_table: str,
        department_table: str,
        branch_table: str,
        account_table: str,
        sub_account_table: str,
        affiliate_table: str,
        product_table: str,
        book_table: str,
        source_table: str,
    ) -> 'RegistryClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                GLSegmentType.ENTITY: entity_table,
                GLSegmentType.DEPARTMENT: department_table,
                GLSegmentType.BRANCH: branch_table,
                GLSegmentType.ACCOUNT: account_table,
                GLSegmentType.SUB_ACCOUNT: sub_account_table,
                GLSegmentType.AFFILIATE: affiliate_table,
                GLSegmentType.PRODUCT: product_table,
                GLSegmentType.BOOK: book_table,
                GLSegmentType.SOURCE: source_table,
            },
        )

        return cls(RegistryRepository(store))


    def validate_segment(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> bool:
        return self._manager.validate_segment(segment, business_dt, segment_cd)


    def get_segment_details(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> DataFrame:
        return self._manager.get_segment_details(segment, business_dt, segment_cd)
