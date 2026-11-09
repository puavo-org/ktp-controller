# Standard library imports
import functools

# Internal imports
import ktp_controller.agent.tasks.base as base
import ktp_controller.api.client

__all__ = [
    "OldExamInfoCleanupTask",
]


class OldExamInfoCleanupTask:
    def __init__(self, *, interval_sec: int, older_than_days: int) -> None:
        self.__interval_sec = interval_sec
        self.__older_than_days = older_than_days

    async def run_ticker(self) -> None:
        await base.periodic(
            "old exam info cleanup",
            self.__interval_sec,
            functools.partial(
                ktp_controller.api.client.delete_old_exam_info,
                older_than_days=self.__older_than_days,
            ),
            on_error_message="old exam info cleanup failed",
        )
