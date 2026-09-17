from pyspark.sql import SparkSession

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from registry import RegistryClient

from break_analysis.tools.registry import RegistryTools
from break_analysis import BreakAnalysisAgent


spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('break-agent-dev')
    .config(
        'spark.jars.packages',
        'org.postgresql:postgresql:42.7.7',
    )
    .getOrCreate()
)


llm = ChatOllama(
    model='qwen3:8b',
    temperature=0
)

registry_client = RegistryClient.from_db(
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

registry_tools = RegistryTools(registry_client=registry_client)

agent = BreakAnalysisAgent(
    llm=llm,
    registry_tools=registry_tools
)

message = HumanMessage(
    content=(
        'Validate GL account 210000 in Registry. '
        'Use the validate_segment tool.'
    )
)
try:
    response = agent._llm_with_tools.invoke([message])
    print(response)
    print(response.tool_calls)
except Exception as e:
    print(f"Error occurred: {e}")
finally:
    spark.stop()

