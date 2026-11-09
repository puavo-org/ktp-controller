# Standard library imports
import functools
import logging

# Internal imports
import ktp_controller.agent.tasks.base as base
import ktp_controller.files

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "FileCleanupTask",
]


class FileCleanupTask:
    def __init__(self, *, interval_sec: int) -> None:
        self.__interval_sec = interval_sec

    async def run_ticker(self) -> None:
        await base.periodic(
            "file cleanup",
            self.__interval_sec,
            functools.partial(ktp_controller.files.cleanup_files, logger=_LOGGER),
            on_error_message="file cleanup failed",
        )
