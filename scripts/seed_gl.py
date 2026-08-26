from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from core.db import PostgresConfig


SEGMENT_DEFAULT_PATH = Path('data/gl/segment_defaults.csv')


def main() -> None:
    # Read everything as string so codes such as leading-zero values are
    # preserved exactly.
    df = pd.read_csv(
        SEGMENT_DEFAULT_PATH,
        dtype=str,
    )

    df.columns = [
        column.lower()
        for column in df.columns
    ]

    db_config = PostgresConfig.from_env()

    engine = create_engine(
        db_config.sqlalchemy_url
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                'TRUNCATE TABLE gl.segment_default'
            )
        )

        df.to_sql(
            name='segment_default',
            con=connection,
            schema='gl',
            if_exists='append',
            index=False,
        )

    print(
        f'Seeded {len(df)} segment defaults into '
        'gl.segment_default'
    )


if __name__ == '__main__':
    main()
