from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from core.db import PostgresConfig


REGISTRY_DIR = Path('data/registry')

TABLES = [
    'gl_entity',
    'gl_dept',
    'gl_branch',
    'gl_account',
    'gl_sub_account',
    'gl_affiliate',
    'gl_product',
    'gl_book',
    'gl_source',
]

DATE_COLUMNS = {
    'business_dt',
}


def load_csv(table_name: str) -> pd.DataFrame:
    path = REGISTRY_DIR / f'{table_name}.csv'

    # Read everything as string initially so identifiers such as
    # codes with leading zeros are preserved exactly.
    df = pd.read_csv(
        path,
        dtype=str,
    )

    df.columns = [
        column.lower()
        for column in df.columns
    ]

    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = df[column].map(
                lambda value: (
                    date.fromisoformat(value)
                    if pd.notna(value)
                    else None
                )
            )

    # Convert pandas NaN/NA values to Python None so they become
    # SQL NULL.
    df = df.astype(object).where(
        pd.notna(df),
        None,
    )

    return df


def seed_table(
    connection,
    table_name: str,
    df: pd.DataFrame,
) -> None:
    physical_table = f'registry.{table_name}'

    connection.execute(
        text(
            f'TRUNCATE TABLE {physical_table}'
        )
    )

    df.to_sql(
        name=table_name,
        con=connection,
        schema='registry',
        if_exists='append',
        index=False,
    )

    print(
        f'Seeded {len(df)} rows into '
        f'{physical_table}.'
    )


def main() -> None:
    db_config = PostgresConfig.from_env()
    engine = create_engine(
        db_config.sqlalchemy_url,
    )

    with engine.begin() as connection:
        for table_name in TABLES:
            df = load_csv(table_name)

            seed_table(
                connection,
                table_name,
                df,
            )

    print('Registry seed completed.')


if __name__ == '__main__':
    main()