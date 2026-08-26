from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from core.db import PostgresConfig


COUNTERPARTY_PATH = Path('data/reference/counterparty.csv')
FX_RATE_PATH = Path('data/reference/fx_rate.csv')


def seed_table(
    connection,
    df: pd.DataFrame,
    table_name: str,
) -> None:
    connection.execute(
        text(
            f'TRUNCATE TABLE {table_name}'
        )
    )

    schema, table = table_name.split('.', maxsplit=1)

    df.to_sql(
        name=table,
        con=connection,
        schema=schema,
        if_exists='append',
        index=False,
    )


def main() -> None:
    db_config = PostgresConfig.from_env()
    engine = create_engine(db_config.sqlalchemy_url)

    counterparty_df = pd.read_csv(
        COUNTERPARTY_PATH,
        parse_dates=['BUSINESS_DT'],
    )

    fx_rate_df = pd.read_csv(
        FX_RATE_PATH,
        parse_dates=['CONVERSION_DT'],
    )

    counterparty_df.columns = [
        column.lower()
        for column in counterparty_df.columns
    ]

    fx_rate_df.columns = [
        column.lower()
        for column in fx_rate_df.columns
    ]

    with engine.begin() as connection:
        seed_table(
            connection,
            counterparty_df,
            'reference.counterparty',
        )

        seed_table(
            connection,
            fx_rate_df,
            'reference.fx_rate',
        )

    print(
        f'Seeded {len(counterparty_df)} counterparties and '
        f'{len(fx_rate_df)} FX rates.'
    )


if __name__ == '__main__':
    main()
