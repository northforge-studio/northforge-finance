import pytest

from finmap import PostingRule

from adi.rules import PostingRuleProcessor


@pytest.fixture(scope='module')
def processor():
    return PostingRuleProcessor()


@pytest.fixture
def df(spark):
    return spark.createDataFrame(
        [
            ('record-1', 'OLD_RULE'),
            ('record-2', 'OLD_RULE'),
        ],
        [
            'RECORD_ID',
            'POSTING_RULE_ID',
        ],
    )


def test_apply_gross_up_overwrites_posting_rule_id(processor, df):
    rule = PostingRule(
        id='TB-GRS-001-BK-01',
        posting_stream='GROSS_UP',
        posting_measure_nm='BALANCE',
    )

    result = processor.apply(df, rule)

    rule_ids = {
        row['POSTING_RULE_ID']
        for row in result.collect()
    }

    assert rule_ids == {'TB-GRS-001-BK-01'}


def test_apply_gross_up_preserves_row_count(processor, df):
    rule = PostingRule(
        id='TB-GRS-001-BK-01',
        posting_stream='GROSS_UP',
        posting_measure_nm='BALANCE',
    )

    result = processor.apply(df, rule)

    assert result.count() == df.count()


def test_apply_tb_offset_overwrites_posting_rule_id(processor, df):
    rule = PostingRule(
        id='DV-GRS-024-BK-02',
        posting_stream='TB_OFFSET',
        posting_measure_nm='NOTIONAL',
    )

    result = processor.apply(df, rule)

    rule_ids = {
        row['POSTING_RULE_ID']
        for row in result.collect()
    }

    assert rule_ids == {'DV-GRS-024-BK-02'}


def test_apply_unsupported_stream_raises(processor, df):
    rule = PostingRule(
        id='DV-GRS-024-BK-99',
        posting_stream='UNKNOWN_STREAM',
        posting_measure_nm='NOTIONAL',
    )

    with pytest.raises(
        ValueError,
        match='UNKNOWN_STREAM',
    ):
        processor.apply(df, rule)
