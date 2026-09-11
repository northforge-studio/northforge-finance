import logging
from uuid import UUID

from core.logging import configure_logging, get_logger, short_id


def test_get_logger_returns_logger_named_after_caller_module():
    logger = get_logger('workflow.orchestrator')

    assert logger.name == 'workflow.orchestrator'


def test_short_id_truncates_uuid_to_first_eight_characters():
    value = UUID('3f9a1e2b-7c44-4d91-9a2e-5b6c8d0f1a23')

    assert short_id(value) == '3f9a1e2b'


def test_short_id_accepts_a_plain_string():
    assert short_id('abcdef0123456789') == 'abcdef01'


def test_configure_logging_sets_root_level_and_a_single_stdout_handler():
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers[:]

    try:
        configure_logging('DEBUG')

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)
    finally:
        root.setLevel(original_level)
        root.handlers = original_handlers
