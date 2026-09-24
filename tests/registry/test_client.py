from datetime import date

import pytest

from registry import RegistryClient
from registry.models import GLSegmentType

from tests.support.paths import (
    REGISTRY_ENTITY_PATH,
    REGISTRY_DEPARTMENT_PATH,
    REGISTRY_BRANCH_PATH,
    REGISTRY_ACCOUNT_PATH,
    REGISTRY_SUB_ACCOUNT_PATH,
    REGISTRY_AFFILIATE_PATH,
    REGISTRY_PRODUCT_PATH,
    REGISTRY_BOOK_PATH,
    REGISTRY_SOURCE_PATH,
)


@pytest.fixture(scope='module')
def registry(spark):
    return RegistryClient.from_csv(
        spark=spark,
        entity_path=REGISTRY_ENTITY_PATH,
        department_path=REGISTRY_DEPARTMENT_PATH,
        branch_path=REGISTRY_BRANCH_PATH,
        account_path=REGISTRY_ACCOUNT_PATH,
        sub_account_path=REGISTRY_SUB_ACCOUNT_PATH,
        affiliate_path=REGISTRY_AFFILIATE_PATH,
        product_path=REGISTRY_PRODUCT_PATH,
        book_path=REGISTRY_BOOK_PATH,
        source_path=REGISTRY_SOURCE_PATH,
    )


def test_validate_segment_is_true_for_active_record(registry):
    assert registry.validate_segment(
        GLSegmentType.ENTITY,
        date(2026, 3, 31),
        'USMKTS',
    ) is True


def test_validate_segment_is_false_for_unknown_segment_cd(registry):
    assert registry.validate_segment(
        GLSegmentType.ENTITY,
        date(2026, 3, 31),
        'UNKNOWN',
    ) is False


def test_validate_segment_is_false_for_unmatched_business_dt(registry):
    assert registry.validate_segment(
        GLSegmentType.ENTITY,
        date(2099, 1, 1),
        'USMKTS',
    ) is False


def test_get_segment_details_returns_active_record(registry):
    result = registry.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USNY01',
    )

    rows = result.collect()
    assert len(rows) == 1
    assert rows[0]['BCH_DS'] == 'New York'
    assert rows[0]['STATUS'] == 'A'


def test_get_segment_details_returns_inactive_record(registry):
    result = registry.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USCH01',
    )

    rows = result.collect()
    assert len(rows) == 1
    assert rows[0]['STATUS'] == 'I'


def test_validate_segment_is_false_for_inactive_record(registry):
    assert registry.validate_segment(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'USCH01',
    ) is False


def test_get_segment_details_returns_empty_when_not_found(registry):
    result = registry.get_segment_details(
        GLSegmentType.BRANCH,
        date(2026, 3, 31),
        'UNKNOWN',
    )

    assert result.count() == 0
