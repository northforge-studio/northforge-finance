from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from core.db import PostgresConfig


META_PATH = Path('data/atlas/mapping_meta.csv')
DATA_PATH = Path('data/atlas/mapping_data.csv')

DATE_COLUMNS = [
    'RCD_DT',
    'EFF_START_DATE',
    'EFF_END_DATE',
]


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for column in DATE_COLUMNS:
        df[column] = df[column].map(date.fromisoformat)

    return df


def seed_table(
    connection,
    df: pd.DataFrame,
    table_name: str,
) -> None:
    connection.execute(
        text(
            f'TRUNCATE TABLE {table_name} '
            f'RESTART IDENTITY'
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

    meta_df = pd.read_csv(META_PATH)

    data_df = pd.read_csv(
        DATA_PATH,
        dtype={
            'WEIGHTAGE': str,
        },
    )

    meta_df = parse_dates(meta_df)
    data_df = parse_dates(data_df)

    meta_df.columns = [
        column.lower()
        for column in meta_df.columns
    ]

    data_df.columns = [
        column.lower()
        for column in data_df.columns
    ]

    with engine.begin() as connection:
        seed_table(
            connection,
            meta_df,
            'atlas.meta',
        )

        seed_table(
            connection,
            data_df,
            'atlas.data',
        )

    print(
        f'Seeded {len(meta_df)} Atlas metadata rows and '
        f'{len(data_df)} Atlas data rows.'
    )


if __name__ == '__main__':
    main()
