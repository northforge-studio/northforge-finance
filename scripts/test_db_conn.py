import os
from dotenv import load_dotenv

from pyspark.sql import SparkSession


load_dotenv()

DB_HOST = os.environ['POSTGRES_HOST']
DB_PORT = os.environ['POSTGRES_PORT']
DB_NAME = os.environ['POSTGRES_DB']
DB_USER = os.environ['POSTGRES_USER']
DB_PASSWORD = os.environ['POSTGRES_PASSWORD']

JDBC_URL = (
    f'jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

DB_PROPERTIES = {
    'user': DB_USER,
    'password': DB_PASSWORD,
    'driver': 'org.postgresql.Driver',
}
TEST_TABLE = 'public.spark_connection_test'


def execute_sql(
    spark: SparkSession,
    sql: str,
) -> None:
    properties = spark._jvm.java.util.Properties()
    properties.setProperty('user', DB_PROPERTIES['user'])
    properties.setProperty('password', DB_PROPERTIES['password'])

    driver = spark._jvm.org.postgresql.Driver()
    connection = driver.connect(
        JDBC_URL,
        properties,
    )

    try:
        statement = connection.createStatement()

        try:
            statement.execute(sql)
        finally:
            statement.close()

    finally:
        connection.close()


def main() -> None:
    spark = (
        SparkSession.builder
        .master('local[*]')
        .appName('db-connection-test')
        .config(
            'spark.jars.packages',
            'org.postgresql:postgresql:42.7.7',
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel('ERROR')

    test_data = [
        (1, 'Postgres connection working'),
        (2, 'Spark JDBC write working'),
    ]

    try:
        print('Testing PostgreSQL connection...')

        # Remove a stale table left by a previous failed run.
        execute_sql(
            spark,
            f'DROP TABLE IF EXISTS {TEST_TABLE}',
        )

        df = spark.createDataFrame(
            test_data,
            ['id', 'message'],
        )

        print('Writing test data...')

        (
            df.write
            .jdbc(
                url=JDBC_URL,
                table=TEST_TABLE,
                mode='overwrite',
                properties=DB_PROPERTIES,
            )
        )

        print('Reading test data...')

        result_df = (
            spark.read
            .jdbc(
                url=JDBC_URL,
                table=TEST_TABLE,
                properties=DB_PROPERTIES,
            )
        )

        result_df.show(truncate=False)

        result = {
            (row['id'], row['message'])
            for row in result_df.collect()
        }

        expected = set(test_data)

        assert result == expected, (
            'Data verification failed.\n'
            f'Expected: {expected}\n'
            f'Actual:   {result}'
        )

        print('PostgreSQL connection test passed.')

    finally:
        print(f'Cleaning up {TEST_TABLE}...')

        try:
            execute_sql(
                spark,
                f'DROP TABLE IF EXISTS {TEST_TABLE}',
            )
            print('Cleanup complete.')

        finally:
            spark.stop()


if __name__ == '__main__':
    main()
