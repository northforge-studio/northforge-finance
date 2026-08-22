import pytest
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from finmap import GatewayRule, PostingRule

from adi.rules import (
    RuleExecutionEngine,
    GatewayRuleProcessor,
    PostingRuleProcessor,
)


@pytest.fixture(scope='module')
def engine():
    gateway_processor = GatewayRuleProcessor(
        posting_rule_processor=PostingRuleProcessor(),
    )

    return RuleExecutionEngine(
        gateway_processor=gateway_processor,
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


def test_execute_single_gateway_single_gross_up(engine, df):
    gateway_rules = [
        GatewayRule(
            id='TB-GRS-001-BK',
            posting_rules=[
                PostingRule(
                    id='TB-GRS-001-BK-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
    ]

    result = engine.execute(
        df=df,
        gateway_rules=gateway_rules,
    )

    assert result.count() == df.count()

    rule_ids = {
        row['POSTING_RULE_ID']
        for row in result.collect()
    }

    assert rule_ids == {'TB-GRS-001-BK-01'}


def test_execute_multiple_gateways(engine, df):
    gateway_rules = [
        GatewayRule(
            id='TB-GRS-001-BK',
            posting_rules=[
                PostingRule(
                    id='TB-GRS-001-BK-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
        GatewayRule(
            id='TB-GRS-002-BK',
            posting_rules=[
                PostingRule(
                    id='TB-GRS-002-BK-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
    ]

    source_count = df.count()

    result = engine.execute(
        df=df,
        gateway_rules=gateway_rules,
    )

    assert result.count() == 2 * source_count

    counts = {
        row['POSTING_RULE_ID']: row['count']
        for row in result.groupBy('POSTING_RULE_ID').count().collect()
    }

    assert counts == {
        'TB-GRS-001-BK-01': source_count,
        'TB-GRS-002-BK-01': source_count,
    }


def test_execute_mixed_gross_up_and_offset_gateways(engine, df):
    gateway_rules = [
        GatewayRule(
            id='GATEWAY-A',
            posting_rules=[
                PostingRule(
                    id='GATEWAY-A-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
        GatewayRule(
            id='GATEWAY-B',
            posting_rules=[
                PostingRule(
                    id='GATEWAY-B-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='NOTIONAL',
                ),
                PostingRule(
                    id='GATEWAY-B-02',
                    posting_stream='TB_OFFSET',
                    posting_measure_nm='NOTIONAL',
                ),
            ],
        ),
    ]

    source_count = df.count()

    result = engine.execute(
        df=df,
        gateway_rules=gateway_rules,
    )

    assert result.count() == 3 * source_count

    counts = {
        row['POSTING_RULE_ID']: row['count']
        for row in result.groupBy('POSTING_RULE_ID').count().collect()
    }

    assert counts == {
        'GATEWAY-A-01': source_count,
        'GATEWAY-B-01': source_count,
        'GATEWAY-B-02': source_count,
    }


def test_execute_no_gateway_rules_raises(engine, df):
    with pytest.raises(
        ValueError,
        match='No gateway rules configured',
    ):
        engine.execute(
            df=df,
            gateway_rules=[],
        )


class _RecordingGatewayProcessor:
    def __init__(self):
        self.seen_row_counts: list[int] = []


    def process(
        self,
        df: DataFrame,
        gateway_rule: GatewayRule,
    ) -> DataFrame:
        self.seen_row_counts.append(df.count())

        return df.withColumn(
            'GATEWAY_RULE_ID',
            F.lit(gateway_rule.id),
        )


def test_execute_invokes_every_gateway_with_original_input(spark, df):
    gateway_rules = [
        GatewayRule(
            id='GATEWAY-A',
            posting_rules=[
                PostingRule(
                    id='GATEWAY-A-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
        GatewayRule(
            id='GATEWAY-B',
            posting_rules=[
                PostingRule(
                    id='GATEWAY-B-01',
                    posting_stream='GROSS_UP',
                    posting_measure_nm='BALANCE',
                ),
            ],
        ),
    ]

    recording_processor = _RecordingGatewayProcessor()

    engine = RuleExecutionEngine(
        gateway_processor=recording_processor,
    )

    source_count = df.count()

    engine.execute(
        df=df,
        gateway_rules=gateway_rules,
    )

    assert recording_processor.seen_row_counts == [
        source_count,
        source_count,
    ]
