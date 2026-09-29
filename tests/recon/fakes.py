class FakeGL:
    """Implements GLClientProtocol; get_postings records each call, every
    other method is unsupported."""

    def __init__(self, postings_by_workflow=None):
        self._postings_by_workflow = postings_by_workflow or {}
        self.get_postings_calls = []

    def get_postings(self, workflow_run_id):
        self.get_postings_calls.append(workflow_run_id)
        return self._postings_by_workflow[workflow_run_id]

    def get_segment_default(self, segment_type, *, entity_cd=None):
        raise NotImplementedError('FakeGL.get_segment_default')

    def get_segment_defaults(self):
        raise NotImplementedError('FakeGL.get_segment_defaults')

    def resolve_segment(
        self, segment_type, segment_value, *, business_dt, entity_cd=None
    ):
        raise NotImplementedError('FakeGL.resolve_segment')

    def resolve_segments(self, segments, *, business_dt):
        raise NotImplementedError('FakeGL.resolve_segments')

    def validate_instruction(self, instruction):
        raise NotImplementedError('FakeGL.validate_instruction')

    def process_instruction(self, instruction):
        raise NotImplementedError('FakeGL.process_instruction')

    def import_instructions(self, identity, source_producer_run_id):
        raise NotImplementedError('FakeGL.import_instructions')

    def rollback_execution(self, identity):
        raise NotImplementedError('FakeGL.rollback_execution')

    def get_rejections(self, workflow_run_id):
        raise NotImplementedError('FakeGL.get_rejections')
