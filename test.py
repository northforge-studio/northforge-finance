def test_finmap():
    from finmap import CsvMappingRepository

    repository = CsvMappingRepository(
        'data/reference/mapping_meta.csv',
    )

    definition = repository.get_definition(
        'ENTITY_MAPPING',
    )

    assert definition.mapping_name == 'ENTITY_MAPPING'
    assert definition.mapping_data_name == 'ENTITY_MAPPING_DATASET'

    assert [
        field.logical_name
        for field in definition.lookup_fields
    ] == [
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
        'COA_RULE_ID',
    ]

    assert [
        field.logical_name
        for field in definition.informational_fields
    ] == [
        'SOURCE_SYSTEM_NAME',
        'ENTITY_NAME',
        'RULE_ID_DESC',
    ]

    assert [
        field.logical_name
        for field in definition.output_fields
    ] == [
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
    ]


def test_transformation_manager():
    from pyspark.sql import SparkSession

    from adi.enrichments import TransformationManager
    from adi.io import CsvTableStore, TrialBalanceReader


    spark = (
        SparkSession.builder
        .master('local[*]')
        .appName('trial-balance-source-read-test')
        .getOrCreate()
    )

    store = CsvTableStore(spark)
    reader = TrialBalanceReader(store)

    df_tb_src = reader.read().limit(5)

    transformation_manager = TransformationManager(spark)

    df_tb_pre_stage = transformation_manager.apply(
        df = df_tb_src,
        dataclass= 'TRIAL_BALANCE',
        zone= 'staging',
        stage= 'pre'
    )

    df_tb_pre_stage.show()

    spark.stop()


if __name__ == '__main__':
    # test_transformation_manager()
    test_finmap()
