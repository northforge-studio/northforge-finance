from pathlib import Path

import pandas as pd
from pyspark.sql.types import StringType
from sqlalchemy import create_engine, text

from core.db import PostgresConfig
from spec.contracts import FILE_LAYOUT_SCHEMA


FILE_LAYOUT_PATH = Path('data/spec/file_layout.csv')


def main() -> None:
    string_columns = [
        field.name.lower()
        for field in FILE_LAYOUT_SCHEMA.fields
        if isinstance(field.dataType, StringType)
    ]

    df = pd.read_csv(
        FILE_LAYOUT_PATH,
        dtype={
            column: str
            for column in string_columns
        },
    )

    df.columns = [
        column.lower()
        for column in df.columns
    ]

    df[string_columns] = df[string_columns].fillna('')

    db_config = PostgresConfig.from_env()

    engine = create_engine(
        db_config.sqlalchemy_url
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                'TRUNCATE TABLE spec.file_layout'
            )
        )

        df.to_sql(
            name='file_layout',
            con=connection,
            schema='spec',
            if_exists='append',
            index=False,
        )

    print(
        f'Seeded {len(df)} file layout rows into '
        'spec.file_layout'
    )


if __name__ == '__main__':
    main()
