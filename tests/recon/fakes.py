class FakeGL:
    '''Duck-types GLClient.get_postings, and records each call.'''

    def __init__(self, postings_by_workflow=None):
        self._postings_by_workflow = postings_by_workflow or {}
        self.get_postings_calls = []


    def get_postings(self, workflow_run_id):
        self.get_postings_calls.append(workflow_run_id)
        return self._postings_by_workflow[workflow_run_id]
