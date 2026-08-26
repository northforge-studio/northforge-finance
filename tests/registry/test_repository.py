from datetime import date

import pytest

from core.store import CsvStore

from registry import SegmentType
from registry.repository import RegistryRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'REGISTRY_GL_ENTITY': 'data/registry/gl_entity.csv',
            'REGISTRY_GL_BRANCH': 'data/registry/gl_branch.csv',
        },
    )
    return RegistryRepository(store)


def test_get_segment_filters_by_business_dt_segment_cd_and_status(repository):
    df = repository.get_segment(
        SegmentType.ENTITY,
        date(2025, 3, 31),
        '505890',
    )

    assert df.count() == 1
    assert df.first()['ENT_DS'] == 'SMBC NIKKO SECURITIES AMERICAS INC.'


def test_get_segment_returns_empty_for_unmatched_segment_cd(repository):
    df = repository.get_segment(
        SegmentType.BRANCH,
        date(2025, 3, 31),
        'UNKNOWN',
    )

    assert df.count() == 0


class _FakeStore:
    """A minimal Store stand-in, to prove RegistryRepository is backend-agnostic."""

    def __init__(self, tables):
        self._tables = tables

    def read(self, table_name, schema=None):
        return self._tables[table_name]


def test_get_segment_works_against_a_fake_store(spark):
    branch_df = spark.createDataFrame(
        [
            (date(2025, 3, 31), '000000', 'NON BRANCH', 'A'),
            (date(2025, 3, 31), '000001', 'INACTIVE BRANCH', 'I'),
        ],
        ['BUSINESS_DT', 'BCH_CD', 'BCH_DS', 'STATUS'],
    )

    store = _FakeStore({'REGISTRY_GL_BRANCH': branch_df})
    repository = RegistryRepository(store)

    df = repository.get_segment(
        SegmentType.BRANCH,
        date(2025, 3, 31),
        '000001',
    )

    assert df.count() == 0
