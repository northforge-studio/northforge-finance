import logging
import sys


_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'


def configure_logging(root_level: str = 'WARNING') -> None:
    '''Configure stdout logging for the application.'''
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.setLevel(root_level)
    root.handlers = [handler]


def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


def short_id(value) -> str:
    '''Truncate a UUID (or any stringable id) to an 8-char display form, git-short-sha style.'''
    return str(value)[:8]
