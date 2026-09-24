import pytest
from pyspark.sql import SparkSession

from tests.support.fakes import make_run_tracker


@pytest.fixture(scope='session')
def spark():
    spark = (
        SparkSession.builder
        .master('local[2]')
        .appName('atlas-tests')
        .getOrCreate()
    )

    yield spark

    spark.stop()


@pytest.fixture
def run_tracker():
    return make_run_tracker()
