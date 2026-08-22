from functools import reduce

from pyspark.sql import DataFrame

from finmap import GatewayRule

from adi.rules.posting import PostingRuleProcessor


class GatewayRuleProcessor:
    def __init__(self, posting_rule_processor: PostingRuleProcessor):
        self._posting_rule_processor = posting_rule_processor


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

        posting_results = [
            self._posting_rule_processor.apply(gateway_df, posting_rule)
            for posting_rule in gateway_rule.posting_rules
        ]

        return reduce(
            lambda left, right: left.unionByName(right),
            posting_results,
        )


    def _preprocess(
        self,
        df: DataFrame,
        gateway_rule: GatewayRule,
    ) -> DataFrame:
        return df
