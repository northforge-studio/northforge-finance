from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from finmap import PostingRule


class PostingRuleProcessor:
    def apply(
        self,
        df: DataFrame,
        rule: PostingRule,
    ) -> DataFrame:
        df = df.withColumn(
            'POSTING_RULE_ID',
            F.lit(rule.id),
        )

        match rule.posting_stream:
            case 'GROSS_UP':
                return self._apply_gross_up(df)

            case 'TB_OFFSET':
                return self._apply_tb_offset(df)

            case _:
                raise ValueError(
                    f'Unsupported posting stream {rule.posting_stream!r} '
                    f'for posting rule {rule.id!r}'
                )


    def _apply_gross_up(
        self,
        df: DataFrame,
    ) -> DataFrame:
        return df


    def _apply_tb_offset(
        self,
        df: DataFrame,
    ) -> DataFrame:
        return df
