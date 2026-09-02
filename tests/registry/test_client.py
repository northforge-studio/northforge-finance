from datetime import date

import pytest

from registry import RegistryClient
from registry.models import SegmentType


@pytest.fixture(scope='module')
def registry(spark):
    return RegistryClient.from_csv(
        spark=spark,
        entity_path='data/registry/gl_entity.csv',
        department_path='data/registry/gl_dept.csv',
        branch_path='data/registry/gl_branch.csv',
        account_path='data/registry/gl_account.csv',
        sub_account_path='data/registry/gl_sub_account.csv',
        affiliate_path='data/registry/gl_affiliate.csv',
        product_path='data/registry/gl_product.csv',
        book_path='data/registry/gl_book.csv',
        source_path='data/registry/gl_source.csv',
    )


def test_validate_segment_is_true_for_active_record(registry):
    assert registry.validate_segment(
        SegmentType.ENTITY,
        date(2026, 3, 31),
        'USMKTS',
    ) is True


def test_validate_segment_is_false_for_unknown_segment_cd(registry):
    assert registry.validate_segment(
        SegmentType.ENTITY,
        date(2026, 3, 31),
        'UNKNOWN',
    ) is False


def test_validate_segment_is_false_for_unmatched_business_dt(registry):
    assert registry.validate_segment(
        SegmentType.ENTITY,
        date(2099, 1, 1),
        'USMKTS',
    ) is False


def test_get_segment_details_returns_matching_record(registry):
    result = registry.get_segment_details(
        SegmentType.BRANCH,
        date(2026, 3, 31),
        'USNY01',
    )

    assert result.count() == 1
    assert result.first()['BCH_DS'] == 'New York'


def test_get_segment_details_raises_when_not_found(registry):
    with pytest.raises(KeyError):
        registry.get_segment_details(
            SegmentType.BRANCH,
            date(2026, 3, 31),
            'UNKNOWN',
        )
