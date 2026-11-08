# Standard library imports
import dataclasses
import functools
import logging
import os
import os.path
import typing

# Third-party imports
import httpx2

# Internal imports
import ktp_controller.agent.tasks.base as base
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "RefreshExamsTask",
]


async def _ensure_exam_file_exists(eom_scheduled_exam: dict[str, typing.Any]) -> None:
    _LOGGER.info(
        "ensuring exam file %r (file_uuid=%s) exists",
        eom_scheduled_exam["file_name"],
        eom_scheduled_exam["file_uuid"],
    )

    utcnow = ktp_controller.utils.utcnow_str()

    filepath = ktp_controller.files.get_local_filepath(
        ktp_controller.files.LocalFilepathType.EXAM_FILE,
        eom_scheduled_exam["file_uuid"],
        eom_scheduled_exam["file_sha256"],
    )

    do_download = False
    if not os.path.exists(filepath):
        do_download = True
    elif os.path.getsize(filepath) != eom_scheduled_exam["file_size"]:
        _LOGGER.warning(
            "exam file %r (file_uuid=%s) is already downloaded, "
            "but Exam-O-Matic claims it has incorrect size, re-downloading it now",
            eom_scheduled_exam["file_name"],
            eom_scheduled_exam["file_uuid"],
        )
        os.rename(
            filepath, f"{filepath}.incorrect_size-{utcnow}"
        )  # Saved for possible investigation.
        do_download = True
    elif ktp_controller.utils.sha256(filepath) != eom_scheduled_exam["file_sha256"]:
        _LOGGER.warning(
            "exam file %r (file_uuid=%s) is already downloaded, "
            "but Exam-O-Matic claims it has incorrect SHA256 checksum, re-downloading it now",
            eom_scheduled_exam["file_name"],
            eom_scheduled_exam["file_uuid"],
        )
        os.rename(
            filepath, f"{filepath}.incorrect_sha256-{utcnow}"
        )  # Saved for possible investigation.
        do_download = True

    if do_download:
        _LOGGER.info(
            "starting to download exam file %r (file_uuid=%s) to %r",
            eom_scheduled_exam["file_name"],
            eom_scheduled_exam["file_uuid"],
            filepath,
        )
        await ktp_controller.examomatic.client.download_exam_file(
            eom_scheduled_exam["file_sha256"], filepath
        )
        _LOGGER.info(
            "downloaded exam file %r (file_uuid=%s) successfully to %r",
            eom_scheduled_exam["file_name"],
            eom_scheduled_exam["file_uuid"],
            filepath,
        )
    else:
        _LOGGER.info(
            "exam file %r (file_uuid=%s) already exists at %r and is up to date",
            eom_scheduled_exam["file_name"],
            eom_scheduled_exam["file_uuid"],
            filepath,
        )
        # Update mtime to avoid deleting this cached file
        # soon. See ktp_controller.files.cleanup_old_exam_files()'
        os.utime(filepath)


async def _refresh_exams(*, is_spontaneous: bool) -> None:
    _LOGGER.info(
        "Starting %sexam refresh...",
        "spontaneous " if is_spontaneous else "requested ",
    )

    try:
        eom_exam_info = await ktp_controller.examomatic.client.get_exam_info()
    except httpx2.HTTPStatusError as http_error:
        if http_error.response.status_code == 404:
            if is_spontaneous:
                # It's ok that there are no exam infos, because we
                # are doing spontaneous refresh and we had no
                # prior knowledge about availability of exam infos.
                _LOGGER.info("No exam info available.")
            else:
                _LOGGER.error(
                    "No exam info available, but we have been told that there should be!"
                )
        else:
            _LOGGER.exception("Failed to refresh exams")
        return
    except Exception:
        _LOGGER.exception("Failed to refresh exams")
        return

    _LOGGER.debug("Received exam info from Exam-O-Matic: %s:", eom_exam_info)

    for eom_scheduled_exam in eom_exam_info["schedules"]:
        await _ensure_exam_file_exists(eom_scheduled_exam)

    await ktp_controller.api.client.save_exam_info(eom_exam_info)

    _LOGGER.info("refreshed exams successfully")


@dataclasses.dataclass(frozen=True)
class _Request:
    is_spontaneous: bool


class RefreshExamsTask:
    """Producer/consumer wrapper around exam refreshing.

    Two sibling asyncio tasks must be scheduled: run_ticker() (the
    periodic producer) and run_consumer() (the task body runner).
    Both the ticker and Agent's REFRESH_EXAM_INFO command handler call
    request_refresh() as producers; at most one refresh is in flight
    and at most one more is guaranteed to run right after it, no
    matter how many callers are waiting (see
    ktp_controller.agent.tasks.base.CoalescingQueue).
    """

    def __init__(self, *, interval_sec: int) -> None:
        self.__interval_sec = interval_sec
        self.__queue: base.CoalescingQueue[_Request, None] = base.CoalescingQueue()

    async def request_refresh(self, *, is_spontaneous: bool) -> None:
        """Producer API for both trigger sources.

        Returns once a run servicing this request (an already
        pending/in-flight run, or a fresh one) has completed.
        """
        await self.__queue.request(_Request(is_spontaneous=is_spontaneous))

    async def run_ticker(self) -> None:
        await base.periodic(
            "periodic exam refresh ticker",
            self.__interval_sec,
            functools.partial(self.request_refresh, is_spontaneous=True),
            on_error_message="Failed to refresh exams",
        )

    async def run_consumer(self) -> None:
        async with base.task_guard("exam refresh consumer"):
            while not base.SHUTDOWN_EVENT.is_set():
                batch = await self.__queue.consume()
                requests = [request for request, _ in batch]
                futures = [future for _, future in batch]
                is_spontaneous = all(request.is_spontaneous for request in requests)
                try:
                    await _refresh_exams(is_spontaneous=is_spontaneous)
                except Exception as exc:
                    base.reject_all(futures, exc)
                else:
                    base.resolve_all(futures, None)
