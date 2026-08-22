from functools import reduce

from pyspark.sql import DataFrame

from finmap import GatewayRule

from adi.rules.gateway import GatewayRuleProcessor


class RuleExecutionEngine:
    def __init__(self, gateway_processor: GatewayRuleProcessor):
        self._gateway_processor = gateway_processor


    def execute(
        self,
        df: DataFrame,
        gateway_rules: list[GatewayRule],
    ) -> DataFrame:
        if not gateway_rules:
            raise ValueError('No gateway rules configured')

        gateway_results = [
            self._gateway_processor.process(df, gateway_rule)
            for gateway_rule in gateway_rules
        ]

        return reduce(
            lambda left, right: left.unionByName(right),
            gateway_results,
        )
