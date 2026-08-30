from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text, Numeric

from core.db import PostgresConfig


SOURCE_PATH = Path('data/source/trial_balance.csv')

DATE_COLUMNS = [
    'as_of_dt',
    'business_dt',
]


def main() -> None:
    db_config = PostgresConfig.from_env()
    engine = create_engine(db_config.sqlalchemy_url)

    df = pd.read_csv(
        SOURCE_PATH,
        keep_default_na=False,
        dtype={
            'src_app_cd': str,
            'src_record_id': str,
            'src_entity_cd': str,
            'src_booking_dept_cd': str,
            'src_account_id': str,
            'src_acct_type': str,
            'src_client_id': str,
            'cpty_ref_id': str,
            'src_measure_nm': str,
            'src_measure_ccy_cd': str,
            'src_measure_trans_amt': str,
            'posting_measure_ccy_cd': str,
        },
    )

    for column in DATE_COLUMNS:
        df[column] = df[column].map(date.fromisoformat)

    df['src_measure_trans_amt'] = (
        df['src_measure_trans_amt']
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
