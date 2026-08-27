from datetime import date

from pyspark.sql import SparkSession

from foundry.repository import TrialBalanceRepository
from foundry.pipeline import TrialBalancePipeline
from foundry.config.settings import (
    CSV_TABLE_LOCATIONS,
    POSTGRES_TABLE_LOCATIONS,
)

from core.store import (
    CsvStore,
    PostgresStore,
)
from core.runs import RunRepository, RunTracker

from atlas import AtlasClient
from reference import ReferenceClient
from spec import SpecClient

from gl import GLClient
from registry import RegistryClient
from workflow import WorkflowOrchestrator


BUSINESS_DT = date(2026, 3, 31)

spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('foundry-dev')
    .config(
        'spark.jars.packages',
        'org.postgresql:postgresql:42.7.7',
    )
    .getOrCreate()
)

store = PostgresStore(
    spark, 
    table_names = POSTGRES_TABLE_LOCATIONS
)

repository = TrialBalanceRepository(store)

spec = SpecClient.from_db(
    spark=spark,
    transformation_table='spec.transformation',
    file_layout_table='spec.file_layout',
)

reference = ReferenceClient.from_db(
    spark = spark,
    fx_rate_table='reference.fx_rate',
    counterparty_table='reference.counterparty',
)

atlas = AtlasClient.from_csv(
    spark=spark,
    metadata_path='data/atlas/mapping_meta.csv',
    data_path='data/atlas/mapping_data.csv',
)

run_tracker = RunTracker(RunRepository())

pipeline = TrialBalancePipeline(
    business_dt=BUSINESS_DT,
    atlas=atlas,
    repository=repository,
    reference=reference,
    spec=spec,
)

registry = RegistryClient.from_db(
    spark=spark,
    entity_table='registry.gl_entity',
    department_table='registry.gl_dept',
    branch_table='registry.gl_branch',
    account_table='registry.gl_account',
    sub_account_table='registry.gl_sub_account',
    affiliate_table='registry.gl_affiliate',
    product_table='registry.gl_product',
    book_table='registry.gl_book',
    source_table='registry.gl_source',
)
gl = GLClient.from_db(
    spark=spark,
    segment_default_table='gl.segment_default',
    registry=registry,
)

orchestrator = WorkflowOrchestrator(
    run_tracker=run_tracker,
    foundry_pipeline=pipeline,
    gl=gl,
)

pipeline_result = orchestrator.run_foundry()

print(f"Pipeline run complete: {pipeline_result}")

business_dt = pipeline.config.business_dt
batch_id = pipeline.config.batch_id

posting_df = repository.read_staging(business_dt=business_dt, batch_id=batch_id)

posting_df.show()

posting_df.printSchema()

spark.stop()
