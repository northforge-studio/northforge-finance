from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import (
    CsvStore,
    PostgresStore
)

from registry.models import SegmentType
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
                SegmentType.ENTITY: Path(entity_path),
                SegmentType.DEPARTMENT: Path(department_path),
                SegmentType.BRANCH: Path(branch_path),
                SegmentType.ACCOUNT: Path(account_path),
                SegmentType.SUB_ACCOUNT: Path(sub_account_path),
                SegmentType.AFFILIATE: Path(affiliate_path),
                SegmentType.PRODUCT: Path(product_path),
                SegmentType.BOOK: Path(book_path),
                SegmentType.SOURCE: Path(source_path),
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
                SegmentType.ENTITY: entity_table,
                SegmentType.DEPARTMENT: department_table,
                SegmentType.BRANCH: branch_table,
                SegmentType.ACCOUNT: account_table,
                SegmentType.SUB_ACCOUNT: sub_account_table,
                SegmentType.AFFILIATE: affiliate_table,
                SegmentType.PRODUCT: product_table,
                SegmentType.BOOK: book_table,
                SegmentType.SOURCE: source_table,
            },
        )

        return cls(RegistryRepository(store))


    def validate_segment(
        self,
        segment: SegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> bool:
        return self._manager.validate_segment(segment, business_dt, segment_cd)


    def get_segment_details(
        self,
        segment: SegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> DataFrame:
        return self._manager.get_segment_details(segment, business_dt, segment_cd)
