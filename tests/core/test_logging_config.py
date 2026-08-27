import logging

from core.logging import configure_logging, get_logger


def test_get_logger_returns_logger_named_after_caller_module():
    logger = get_logger('workflow.orchestrator')

    assert logger.name == 'workflow.orchestrator'


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
