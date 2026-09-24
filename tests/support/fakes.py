from dataclasses import replace

from core.runs import RunRepository, RunTracker


class FakeRunRepository(RunRepository):
    '''An in-memory stand-in for RunRepository, so RunTracker (the real,
    unmocked collaborator) can run without a database.'''

    def __init__(self):
        self.workflows = {}
        self.executions = {}
        self.dependencies = []


    def create_workflow_run(self, run):
        self.workflows[run.workflow_run_id] = run


    def get_workflow_run(self, workflow_run_id):
        if workflow_run_id not in self.workflows:
            raise KeyError(f'Unknown workflow_run_id: {workflow_run_id!r}')
        return self.workflows[workflow_run_id]


    def create_execution_run(self, run):
        self.executions[run.run_id] = run


    def get_execution_run(self, run_id):
        return self.executions[run_id]


    def get_execution_runs(self, workflow_run_id):
        return tuple(
            execution
            for execution in self.executions.values()
            if execution.workflow_run_id == workflow_run_id
        )


    def update_workflow_status(self, workflow_run_id, status, completed_at=None):
        run = self.workflows[workflow_run_id]
        self.workflows[workflow_run_id] = replace(
            run, status=status, completed_at=completed_at,
        )


    def update_execution_status(self, run_id, status, completed_at=None):
        run = self.executions[run_id]
        self.executions[run_id] = replace(
            run, status=status, completed_at=completed_at,
        )


    def create_dependency(self, dependency):
        self.dependencies.append(dependency)


def make_run_tracker() -> RunTracker:
    return RunTracker(FakeRunRepository())


class FakeStore:
    '''A minimal in-memory Store stand-in, to prove a repository is
    backend-agnostic.'''

    def __init__(self, tables):
        self._tables = tables


    def read(self, table_name, schema=None):
        return self._tables[table_name]


    def write(self, df, table_name, mode='append'):
        self._tables[table_name] = df


class FakeRegistryClient:
    '''Duck-types RegistryClient.validate_segment, and records each call.'''

    def __init__(self, valid_segments=()):
        self._valid_segments = valid_segments
        self.calls = []


    def validate_segment(self, segment, business_dt, segment_cd):
        self.calls.append((segment, business_dt, segment_cd))
        return (segment, business_dt, segment_cd) in self._valid_segments
