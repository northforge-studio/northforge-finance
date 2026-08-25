from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from foundry.rules.posting import PostingRuleProcessor

from atlas import AtlasClient, GatewayRule
from spec import SpecClient


class GatewayRuleProcessor:
    def __init__(
        self,
        posting_rule_processor: PostingRuleProcessor,
        spec: SpecClient,
        atlas: AtlasClient,
    ):
        self._posting_rule_processor = posting_rule_processor
        self._spec = spec
        self._atlas = atlas


    def process(
        self,
        df: DataFrame,
        gateway_rule: GatewayRule,
    ) -> DataFrame:
        if not gateway_rule.posting_rules:
            raise ValueError(
                f'Gateway rule {gateway_rule.id!r} has no posting rules'
            )

        gateway_df = self._preprocess(df, gateway_rule)

        gateway_pef_df = gateway_df.filter(F.col('POSTING_ELIG_FLG') == 'Y')
        gateway_non_pef_df = gateway_df.filter(
            (F.col('POSTING_ELIG_FLG') != 'Y')
            | F.col('POSTING_ELIG_FLG').isNull()
        )

        posting_results = [
            self._posting_rule_processor.apply(
                gateway_pef_df,
                posting_rule
            )
            for posting_rule in gateway_rule.posting_rules
        ]

        gateway_pef_df = reduce(
            lambda left, right: left.unionByName(right),
            posting_results,
        )

        return gateway_non_pef_df.unionByName(
            gateway_pef_df,
            allowMissingColumns=True
        )


    def _preprocess(
        self,
        df: DataFrame,
        gateway_rule: GatewayRule,
    ) -> DataFrame:
        df = df.withColumn(
            'POSTING_RULE_ID',
            F.lit(gateway_rule.id)
        )

        df = self._atlas.apply(df, mapping_name='POSTING_RULES_MAPPING')
        df = df.filter(F.col('POSTING_SWITCH') == 'ON')

        df = self._atlas.apply(df, mapping_name='PE_TB_MAPPING')

        return df
