from typing import Protocol

from pyspark.sql import DataFrame


class Repository(Protocol):
    def get_fx_rate(self) -> DataFrame:
        ...


    def get_counterparty(self) -> DataFrame:
        ...
