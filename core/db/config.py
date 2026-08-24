import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


    @classmethod
    def from_env(cls) -> 'PostgresConfig':
        return cls(
            host=os.environ['POSTGRES_HOST'],
            port=int(os.environ['POSTGRES_PORT']),
            database=os.environ['POSTGRES_DB'],
            user=os.environ['POSTGRES_USER'],
            password=os.environ['POSTGRES_PASSWORD'],
        )


    @property
    def sqlalchemy_url(self) -> str:
        return (
            f'postgresql+psycopg://'
            f'{self.user}:{self.password}@'
            f'{self.host}:{self.port}/'
            f'{self.database}'
        )


    @property
    def jdbc_url(self) -> str:
        return (
            f'jdbc:postgresql://'
            f'{self.host}:{self.port}/'
            f'{self.database}'
        )


    @property
    def jdbc_properties(self) -> dict[str, str]:
        return {
            'user': self.user,
            'password': self.password,
            'driver': 'org.postgresql.Driver',
            # Allows Spark's string-typed run-identity literals to write
            # into Postgres UUID columns without an explicit cast.
            'stringtype': 'unspecified',
        }
