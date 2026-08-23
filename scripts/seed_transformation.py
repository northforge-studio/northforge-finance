from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from core.db import PostgresConfig


TRANSFORMATIONS_PATH = Path('data/foundry/config/transformations.csv')


def main() -> None:
    df = pd.read_csv(
        TRANSFORMATIONS_PATH,
        dtype={
            'SRC_APP_CD': str,
        },
    )

    df.columns = [column.lower() for column in df.columns]

    db_config = PostgresConfig.from_env()

    engine = create_engine(
        db_config.sqlalchemy_url
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                'TRUNCATE TABLE foundry_config.transformation '
                'RESTART IDENTITY'
            )
        )

        df.to_sql(
            name='transformation',
            con=connection,
            schema='foundry_config',
            if_exists='append',
            index=False,
        )

    print(
        f'Seeded {len(df)} transformations into '
        'foundry_config.transformation'
    )


if __name__ == '__main__':
    main()
