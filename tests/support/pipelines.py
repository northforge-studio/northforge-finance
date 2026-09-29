from typing import TypeVar
from unittest.mock import MagicMock

from foundry.models import PipelineConfig
from foundry.pipeline.base import BasePipeline
from tests.support.constants import BUSINESS_DT


class NoOpPipeline(BasePipeline):
    """A BasePipeline whose main_ hooks pass the DataFrame through, post_
    hooks do nothing and pre_ hooks are unsupported. Zone tests subclass it
    and override only the hooks of the zone under test."""

    def pre_staging(self):
        raise NotImplementedError('NoOpPipeline.pre_staging')

    def main_staging(self, df):
        return df

    def post_staging(self, df): ...

    def pre_enrichment(self, workflow_run_id):
        raise NotImplementedError('NoOpPipeline.pre_enrichment')

    def main_enrichment(self, df):
        return df

    def post_enrichment(self, df): ...

    def pre_reporting(self, workflow_run_id):
        raise NotImplementedError('NoOpPipeline.pre_reporting')

    def main_reporting(self, df):
        return df

    def post_reporting(self, df): ...

    def pre_posting(self, workflow_run_id):
        raise NotImplementedError('NoOpPipeline.pre_posting')

    def main_posting(self, df):
        return df

    def post_posting(self, df): ...

    def pre_interface(self, workflow_run_id):
        raise NotImplementedError('NoOpPipeline.pre_interface')

    def main_interface(self, df):
        return df

    def post_interface(self, df): ...

    def rollback_execution(self, operation, identity): ...


P = TypeVar('P', bound=NoOpPipeline)


def make_pipeline(pipeline_cls: type[P] = NoOpPipeline, **kwargs) -> P:
    return pipeline_cls(
        config=PipelineConfig(
            dataclass='TRIAL_BALANCE',
            business_dt=BUSINESS_DT,
        ),
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
        **kwargs,
    )
