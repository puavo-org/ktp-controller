# Standard library imports
import importlib.metadata
import logging

# Relative imports
from .settings import Settings


def set_logging_level(level: str):
    logging.basicConfig(
        level=logging.getLevelNamesMapping()[level.upper()],
        format=DEFAULT_LOGGING_FORMAT,
        force=True,
    )


VERSION = importlib.metadata.version("ktp-controller")

DEFAULT_LOGGING_LEVEL = logging.INFO
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s:%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(message)s"
)

_LOGGER = logging.getLogger(__name__)

SETTINGS = Settings()
set_logging_level(SETTINGS.logging_level)
_LOGGER.info("Using following settings: %s", SETTINGS)
