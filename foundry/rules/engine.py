from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from atlas import GatewayRule

from foundry.rules.gateway import GatewayRuleProcessor


class RuleExecutionEngine:
    def __init__(self, gateway_rule_processor: GatewayRuleProcessor):
        self._gateway_rule_processor = gateway_rule_processor


    def execute(
        self,
        df: DataFrame,
        gateway_rules: list[GatewayRule],
    ) -> DataFrame:
        if not gateway_rules:
            raise ValueError('No gateway rules configured')

        gateway_results = [
            self._gateway_rule_processor.process(
                df.filter(
                    F.upper(F.col('POSTING_MEASURE_NM')) == F.upper(F.lit(gateway_rule.posting_measure_nm))
                ),
                gateway_rule
            )
            for gateway_rule in gateway_rules
        ]

        return reduce(
            lambda left, right: left.unionByName(right),
            gateway_results,
        )
