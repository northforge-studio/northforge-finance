from datetime import date

import pytest

from core.store import CsvStore

from registry.models import GLSegmentType
from registry.repository import RegistryRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            GLSegmentType.ENTITY: 'data/registry/gl_entity.csv',
            GLSegmentType.BRANCH: 'data/registry/gl_branch.csv',
        },
    )
    return RegistryRepository(store)


def test_get_active_segment_filters_by_business_dt_segment_cd_and_status(repository):
    df = repository.get_active_segment(
        GLSegmentType.ENTITY,
        date(2026, 3, 31),
        'USMKTS',
    )

    assert df.count() == 1
    assert df.first()['ENT_DS'] == 'NorthForge Markets US'


def test_get_active_segment_returns_empty_for_unmatched_segment_cd(repository):
    df = repository.get_active_segment(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'UNKNOWN',
    )

    assert df.count() == 0


def test_get_active_segment_returns_empty_for_inactive_record(repository):
    df = repository.get_active_segment(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USCH01',
    )

    assert df.count() == 0


def test_get_segment_details_returns_active_record(repository):
    df = repository.get_segment_details(
        GLSegmentType.ENTITY,
        date(2026, 3, 31),
        'USMKTS',
    )

    assert df.count() == 1
    assert df.first()['STATUS'] == 'A'


def test_get_segment_details_returns_inactive_record(repository):
    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USCH01',
    )

    assert df.count() == 1
    assert df.first()['STATUS'] == 'I'


def test_get_segment_details_returns_empty_for_unmatched_segment_cd(repository):
    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'UNKNOWN',
    )

    assert df.count() == 0


class _FakeStore:
    """A minimal Store stand-in, to prove RegistryRepository is backend-agnostic."""

    def __init__(self, tables):
        self._tables = tables

    def read(self, table_name, schema=None):
        return self._tables[table_name]


def test_get_active_segment_works_against_a_fake_store(spark):
    branch_df = spark.createDataFrame(
        [
            (date(2025, 3, 31), '000000', 'NON BRANCH', 'A'),
            (date(2025, 3, 31), '000001', 'INACTIVE BRANCH', 'I'),
        ],
        ['BUSINESS_DT', 'BCH_CD', 'BCH_DS', 'STATUS'],
    )

    store = _FakeStore({GLSegmentType.BRANCH: branch_df})
    repository = RegistryRepository(store)

    df = repository.get_active_segment(
        GLSegmentType.BRANCH,
        date(2025, 3, 31),
        '000001',
    )

    assert df.count() == 0


def test_get_segment_details_works_against_a_fake_store(spark):
    branch_df = spark.createDataFrame(
        [
            (date(2025, 3, 31), '000000', 'NON BRANCH', 'A'),
            (date(2025, 3, 31), '000001', 'INACTIVE BRANCH', 'I'),
        ],
        ['BUSINESS_DT', 'BCH_CD', 'BCH_DS', 'STATUS'],
    )

    store = _FakeStore({GLSegmentType.BRANCH: branch_df})
    repository = RegistryRepository(store)

    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2025, 3, 31),
        '000001',
    )

    assert df.count() == 1
    assert df.first()['STATUS'] == 'I'
