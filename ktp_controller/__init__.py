# Standard library imports
import importlib.metadata
import logging

VERSION = importlib.metadata.version("ktp-controller")

DEFAULT_LOGGING_LEVEL = logging.INFO
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s:%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(message)s"
)

logging.basicConfig(
    level=DEFAULT_LOGGING_LEVEL,
    format=DEFAULT_LOGGING_FORMAT,
)
