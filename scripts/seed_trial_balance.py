from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text, Numeric

from core.db import PostgresConfig


SOURCE_PATH = Path('data/source/trial_balance.csv')

DATE_COLUMNS = [
    'AS_OF_DT',
    'BUSINESS_DT',
]


def main() -> None:
    db_config = PostgresConfig.from_env()
    engine = create_engine(db_config.sqlalchemy_url)

    df = pd.read_csv(
        SOURCE_PATH,
        keep_default_na=False,
        dtype={
            'SRC_APP_CD': str,
            'SRC_RECORD_ID': str,
            'SRC_ENTITY_CD': str,
            'SRC_BOOKING_DEPT_CD': str,
            'SRC_ACCOUNT_ID': str,
            'SRC_ACCT_TYPE': str,
            'SRC_CLIENT_ID': str,
            'CPTY_REF_ID': str,
            'SRC_MEASURE_NM': str,
            'SRC_MEASURE_CCY_CD': str,
            'SRC_MEASURE_TRANS_AMT': str,
            'POSTING_MEASURE_CCY_CD': str,
        },
    )

    for column in DATE_COLUMNS:
        df[column] = df[column].map(date.fromisoformat)

    df['SRC_MEASURE_TRANS_AMT'] = (
        df['SRC_MEASURE_TRANS_AMT']
        .map(Decimal)
    )

    df.columns = [
        column.lower()
        for column in df.columns
    ]

    with engine.begin() as connection:
        connection.execute(
            text(
                'TRUNCATE TABLE foundry_source.trial_balance'
            )
        )

        df.to_sql(
            name='trial_balance',
            con=connection,
            schema='foundry_source',
            if_exists='append',
            index=False,
            dtype={
                'src_measure_trans_amt': Numeric(28, 12),
            },
        )

    print(
        f'Seeded {len(df)} Trial Balance source records into '
        'foundry_source.trial_balance.'
    )


if __name__ == '__main__':
    main()
