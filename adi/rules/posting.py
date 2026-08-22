from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from adi.enrichments import TransformationManager

from finmap import FinMapClient, PostingRule


class PostingRuleProcessor:
    def __init__(
        self, 
        dataclass: str,
        transformation_manager: TransformationManager,
        finmap: FinMapClient,
    ):
        self._dataclass = dataclass
        self._transformation_manager = transformation_manager
        self._finmap = finmap


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

        df = self._transformation_manager.apply(
            df,
            dataclass=self._dataclass,
            zone='ENR',
            stage='PRE',
            sub_stage='PRE_COA'
        )

        df = self._apply_coa_enrichments(df)

        df = self._transformation_manager.apply(
            df,
            dataclass=self._dataclass,
            zone='ENR',
            stage='PRE',
            sub_stage='POST_COA'
        )
        
        return df


    def _apply_tb_offset(
        self,
        df: DataFrame,
    ) -> DataFrame:
        return df


    def _apply_coa_enrichments(self, df: DataFrame) -> DataFrame:
        df = self._finmap.apply(df, mapping_name='ENTITY_MAPPING')
        df = self._finmap.apply(df, mapping_name='DEPARTMENT_MAPPING')
        df = self._finmap.apply(df, mapping_name='AFFILIATE_CODE_MAPPING')
        df = self._finmap.apply(df, mapping_name='ACCOUNT_TB_MAPPING')
        df = self._finmap.apply(df, mapping_name='CR_DR_MAPPING')

        return df
