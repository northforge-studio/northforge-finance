import pytest

from finmap import GatewayRule, PostingRule

from adi.rules import GatewayRuleProcessor, PostingRuleProcessor


@pytest.fixture(scope='module')
def processor():
    return GatewayRuleProcessor(
        posting_rule_processor=PostingRuleProcessor(),
    )


@pytest.fixture
def df(spark):
    return spark.createDataFrame(
        [
            ('record-1',),
            ('record-2',),
        ],
        [
            'RECORD_ID',
        ],
    )


def test_process_gross_up_only(processor, df):
    gateway_rule = GatewayRule(
        id='TB-GRS-001-BK',
        posting_rules=[
            PostingRule(
                id='TB-GRS-001-BK-01',
                posting_stream='GROSS_UP',
                posting_measure_nm='BALANCE',
            ),
        ],
    )

    result = processor.process(df, gateway_rule)

    rule_ids = {
        row['POSTING_RULE_ID']
        for row in result.collect()
    }

    assert rule_ids == {'TB-GRS-001-BK-01'}
    assert result.count() == df.count()


def test_process_gross_up_and_offset_share_same_gateway_input(processor, df):
    gateway_rule = GatewayRule(
        id='DV-GRS-024-BK',
        posting_rules=[
            PostingRule(
                id='DV-GRS-024-BK-01',
                posting_stream='GROSS_UP',
                posting_measure_nm='NOTIONAL',
            ),
            PostingRule(
                id='DV-GRS-024-BK-02',
                posting_stream='TB_OFFSET',
                posting_measure_nm='NOTIONAL',
            ),
        ],
    )

    source_count = df.count()

    result = processor.process(df, gateway_rule)

    assert result.count() == 2 * source_count

    counts = {
        row['POSTING_RULE_ID']: row['count']
        for row in result.groupBy('POSTING_RULE_ID').count().collect()
    }

    assert counts == {
        'DV-GRS-024-BK-01': source_count,
        'DV-GRS-024-BK-02': source_count,
    }


def test_process_gateway_with_no_posting_rules_raises(processor, df):
    gateway_rule = GatewayRule(
        id='EMPTY-GATEWAY',
        posting_rules=[],
    )

    with pytest.raises(
        ValueError,
        match='EMPTY-GATEWAY',
    ):
        processor.process(df, gateway_rule)
