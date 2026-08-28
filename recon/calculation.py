from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

from recon.contracts import RECON_KEYS


# Matches the precision/scale of ACCOUNTED_AMOUNT (the only input column
# summed here) and of recon.result's balance columns.
_BALANCE_TYPE = DecimalType(28, 12)


def calculate_recon(interface_df: DataFrame, gl_df: DataFrame) -> DataFrame:
    interface_balance = (
        interface_df
        .groupBy(*RECON_KEYS)
        .agg(F.sum('ACCOUNTED_AMOUNT').alias('INTERFACE_BALANCE'))
    )

    gl_balance = (
        gl_df
        .groupBy(*RECON_KEYS)
        .agg(F.sum('ACCOUNTED_AMOUNT').alias('GL_BALANCE'))
    )

    joined = interface_balance.join(gl_balance, on=list(RECON_KEYS), how='full_outer')

    zero = F.lit(0).cast(_BALANCE_TYPE)
    interface_balance_col = F.coalesce(F.col('INTERFACE_BALANCE'), zero).cast(_BALANCE_TYPE)
    gl_balance_col = F.coalesce(F.col('GL_BALANCE'), zero).cast(_BALANCE_TYPE)

    return (
        joined
        .withColumn('INTERFACE_BALANCE', interface_balance_col)
        .withColumn('GL_BALANCE', gl_balance_col)
        .withColumn(
            'DIFFERENCE_AMOUNT',
            (F.col('INTERFACE_BALANCE') - F.col('GL_BALANCE')).cast(_BALANCE_TYPE),
        )
        .select(*RECON_KEYS, 'INTERFACE_BALANCE', 'GL_BALANCE', 'DIFFERENCE_AMOUNT')
    )
