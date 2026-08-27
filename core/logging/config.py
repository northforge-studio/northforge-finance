import logging
import sys


_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'


def configure_logging(level: str = 'INFO') -> None:
    """Configure stdout logging for the application. Call once from an
    application entry point (e.g. main.ipynb, scripts/test_foundry.py) —
    never from library/application modules."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
