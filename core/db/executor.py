from typing import Any

from sqlalchemy import create_engine, text

from core.db.config import PostgresConfig


class PostgresExecutor:
    def __init__(self, config: PostgresConfig):
        self._engine = create_engine(config.sqlalchemy_url)


    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(sql),
                parameters or {},
            )
