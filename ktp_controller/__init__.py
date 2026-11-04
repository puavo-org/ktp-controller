# Standard library imports
import importlib.metadata
import logging
import os as _os
import pathlib

# Relative imports
from .settings import Settings

__all__ = [
    "DATADIR",
    "DEFAULT_LOGGING_FORMAT",
    "DEFAULT_LOGGING_LEVEL",
    "HOMEDIR",
    "SETTINGS",
    "VERSION",
    "WORKDIR",
    "is_prod_mode",
    "set_logging_level",
]


def is_prod_mode() -> bool:
    return _os.environ.get("_KTPC_PROD_MODE") is not None


HOMEDIR = str(pathlib.Path.home().resolve(strict=True))
WORKDIR = _os.getcwd()

if is_prod_mode():
    DATADIR = str(pathlib.Path(HOMEDIR) / ".local" / "share" / "ktp-controller")
else:
    DATADIR = WORKDIR


def set_logging_level(level: str) -> None:
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
