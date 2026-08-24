from typing import Any, Mapping

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


    def fetch_one(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> Mapping[str, Any] | None:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(sql),
                parameters or {},
            ).mappings().first()

        return dict(row) if row is not None else None


    def fetch_all(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Mapping[str, Any]]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(sql),
                parameters or {},
            ).mappings().all()

        return [dict(row) for row in rows]
