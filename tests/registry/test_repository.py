from datetime import date

import pytest

from core.store import CsvStore
from registry.models import GLSegmentType
from registry.repository import RegistryRepository

from tests.support.fakes import FakeStore
from tests.support.paths import REGISTRY_ENTITY_PATH, REGISTRY_BRANCH_PATH


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            GLSegmentType.ENTITY: REGISTRY_ENTITY_PATH,
            GLSegmentType.BRANCH: REGISTRY_BRANCH_PATH,
        },
    )
    return RegistryRepository(store)


def test_get_active_segment_filters_by_business_dt_segment_cd_and_status(repository):
    df = repository.get_active_segment(
        GLSegmentType.ENTITY,
        date(2026, 3, 31),
        'USMKTS',
    )

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['ENT_DS'] == 'NorthForge Markets US'


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

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['STATUS'] == 'A'


def test_get_segment_details_returns_inactive_record(repository):
    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USCH01',
    )

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['STATUS'] == 'I'


def test_get_segment_details_returns_empty_for_unmatched_segment_cd(repository):
    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'UNKNOWN',
    )

    assert df.count() == 0


def test_get_active_segment_works_against_a_fake_store(spark):
    branch_df = spark.createDataFrame(
        [
            (date(2025, 3, 31), '000000', 'NON BRANCH', 'A'),
            (date(2025, 3, 31), '000001', 'INACTIVE BRANCH', 'I'),
        ],
        schema=['BUSINESS_DT', 'BCH_CD', 'BCH_DS', 'STATUS'],
    )

    store = FakeStore({GLSegmentType.BRANCH: branch_df})
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
        schema=['BUSINESS_DT', 'BCH_CD', 'BCH_DS', 'STATUS'],
    )

    store = FakeStore({GLSegmentType.BRANCH: branch_df})
    repository = RegistryRepository(store)

    df = repository.get_segment_details(
        GLSegmentType.BRANCH,
        date(2025, 3, 31),
        '000001',
    )

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['STATUS'] == 'I'
