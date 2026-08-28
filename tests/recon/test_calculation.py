from datetime import date
from decimal import Decimal

import pytest

from pyspark.sql.types import (
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
)

from recon.calculation import calculate_recon
from recon.contracts import RECON_KEYS


_KEY_FIELDS = [
    StructField('WORKFLOW_RUN_ID', StringType(), False),
    StructField('AS_OF_DATE', DateType(), False),
    StructField('ENTITY_CD', StringType(), False),
    StructField('DEPT_CD', StringType(), False),
    StructField('BRANCH_CD', StringType(), False),
    StructField('GL_ACCOUNT', StringType(), False),
    StructField('SUB_ACCOUNT', StringType(), False),
    StructField('AFFILIATE_CD', StringType(), False),
    StructField('PRODUCT_CD', StringType(), False),
    StructField('BOOK_CD', StringType(), False),
    StructField('SOURCE_CD', StringType(), False),
    StructField('ACCOUNTED_CURRENCY', StringType(), False),
]

# Schema deliberately mirrors only what calculate_recon needs (RECON_KEYS
# + ACCOUNTED_AMOUNT), to prove the function does not depend on the full
# Interface/GL physical schemas.
_SIDE_SCHEMA = StructType(_KEY_FIELDS + [
    StructField('ACCOUNTED_AMOUNT', DecimalType(28, 12), False),
])

# A variant that also carries CR_DR_IND, to prove it plays no part in
# grouping or the balance calculation.
_SIDE_SCHEMA_WITH_CR_DR_IND = StructType(_KEY_FIELDS + [
    StructField('ACCOUNTED_AMOUNT', DecimalType(28, 12), False),
    StructField('CR_DR_IND', StringType(), False),
])

_DEFAULT_KEY = dict(
    WORKFLOW_RUN_ID='11111111-1111-1111-1111-111111111111',
    AS_OF_DATE=date(2026, 1, 1),
    ENTITY_CD='USM',
    DEPT_CD='4000',
    BRANCH_CD='100',
    GL_ACCOUNT='123456',
    SUB_ACCOUNT='001',
    AFFILIATE_CD='AFF1',
    PRODUCT_CD='PRD1',
    BOOK_CD='BK1',
    SOURCE_CD='SRC1',
    ACCOUNTED_CURRENCY='USD',
)


def _row(amount, cr_dr_ind=None, **key_overrides):
    key = dict(_DEFAULT_KEY)
    key.update(key_overrides)

    values = tuple(key[field.name] for field in _KEY_FIELDS) + (amount,)
    if cr_dr_ind is not None:
        values += (cr_dr_ind,)

    return values


def _df(spark, rows, with_cr_dr_ind=False):
    schema = _SIDE_SCHEMA_WITH_CR_DR_IND if with_cr_dr_ind else _SIDE_SCHEMA
    return spark.createDataFrame(list(rows), schema=schema)


def _result_rows(spark, interface_rows, gl_rows, with_cr_dr_ind=False):
    interface_df = _df(spark, interface_rows, with_cr_dr_ind)
    gl_df = _df(spark, gl_rows, with_cr_dr_ind)

    return calculate_recon(interface_df, gl_df).collect()


def test_output_has_recon_keys_plus_balance_columns(spark):
    rows = calculate_recon(
        _df(spark, [_row(Decimal('100.00'))]),
        _df(spark, [_row(Decimal('100.00'))]),
    )

    assert rows.columns == list(RECON_KEYS) + [
        'INTERFACE_BALANCE', 'GL_BALANCE', 'DIFFERENCE_AMOUNT',
    ]


def test_perfect_match_yields_zero_difference(spark):
    rows = _result_rows(
        spark,
        interface_rows=[_row(Decimal('100.00'))],
        gl_rows=[_row(Decimal('100.00'))],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('100.00')
    assert rows[0]['GL_BALANCE'] == Decimal('100.00')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')


def test_interface_only_balance(spark):
    rows = _result_rows(
        spark,
        interface_rows=[_row(Decimal('250.00'))],
        gl_rows=[],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('250.00')
    assert rows[0]['GL_BALANCE'] == Decimal('0')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('250.00')


def test_gl_only_balance(spark):
    rows = _result_rows(
        spark,
        interface_rows=[],
        gl_rows=[_row(Decimal('75.00'))],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('0')
    assert rows[0]['GL_BALANCE'] == Decimal('75.00')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('-75.00')


def test_non_zero_difference(spark):
    rows = _result_rows(
        spark,
        interface_rows=[_row(Decimal('100.00'))],
        gl_rows=[_row(Decimal('90.00'))],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('100.00')
    assert rows[0]['GL_BALANCE'] == Decimal('90.00')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('10.00')


def test_multiple_source_rows_collapse_into_one_recon_grain(spark):
    # Two Interface rows and two GL rows share the same RECON_KEYS grain;
    # each side must be summed down to a single balance before joining.
    rows = _result_rows(
        spark,
        interface_rows=[_row(Decimal('60.00')), _row(Decimal('40.00'))],
        gl_rows=[_row(Decimal('30.00')), _row(Decimal('70.00'))],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('100.00')
    assert rows[0]['GL_BALANCE'] == Decimal('100.00')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')


def test_different_recon_key_combinations_remain_separate(spark):
    rows = _result_rows(
        spark,
        interface_rows=[
            _row(Decimal('100.00'), GL_ACCOUNT='111111'),
            _row(Decimal('200.00'), GL_ACCOUNT='222222'),
        ],
        gl_rows=[
            _row(Decimal('100.00'), GL_ACCOUNT='111111'),
        ],
    )

    by_account = {row['GL_ACCOUNT']: row for row in rows}

    assert set(by_account) == {'111111', '222222'}
    assert by_account['111111']['INTERFACE_BALANCE'] == Decimal('100.00')
    assert by_account['111111']['GL_BALANCE'] == Decimal('100.00')
    assert by_account['111111']['DIFFERENCE_AMOUNT'] == Decimal('0.00')
    assert by_account['222222']['INTERFACE_BALANCE'] == Decimal('200.00')
    assert by_account['222222']['GL_BALANCE'] == Decimal('0')
    assert by_account['222222']['DIFFERENCE_AMOUNT'] == Decimal('200.00')


def test_preserves_exact_decimal_precision(spark):
    rows = _result_rows(
        spark,
        interface_rows=[
            _row(Decimal('100.123456789012')),
            _row(Decimal('100.123456789012')),
        ],
        gl_rows=[_row(Decimal('200.246913578023'))],
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('200.246913578024')
    assert isinstance(rows[0]['INTERFACE_BALANCE'], Decimal)
    assert rows[0]['GL_BALANCE'] == Decimal('200.246913578023')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('0.000000000001')


def test_ignores_cr_dr_ind_in_grouping_and_calculation(spark):
    # Same RECON_KEYS grain, contradictory CR_DR_IND values: if CR_DR_IND
    # were used for grouping or sign derivation this would either split
    # into two rows or produce a different balance than the plain sum of
    # ACCOUNTED_AMOUNT.
    rows = _result_rows(
        spark,
        interface_rows=[
            _row(Decimal('100.00'), cr_dr_ind='DR'),
            _row(Decimal('-40.00'), cr_dr_ind='CR'),
        ],
        gl_rows=[_row(Decimal('60.00'), cr_dr_ind='DR')],
        with_cr_dr_ind=True,
    )

    assert len(rows) == 1
    assert rows[0]['INTERFACE_BALANCE'] == Decimal('60.00')
    assert rows[0]['GL_BALANCE'] == Decimal('60.00')
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')


def test_calculates_without_a_cr_dr_ind_column_present(spark):
    # calculate_recon must not require CR_DR_IND to exist at all.
    rows = _result_rows(
        spark,
        interface_rows=[_row(Decimal('10.00'))],
        gl_rows=[_row(Decimal('10.00'))],
        with_cr_dr_ind=False,
    )

    assert len(rows) == 1
    assert rows[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')


def test_both_sides_empty_yields_no_rows(spark):
    rows = _result_rows(spark, interface_rows=[], gl_rows=[])

    assert rows == []
