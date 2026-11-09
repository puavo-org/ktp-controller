# Standard library imports
import dataclasses
import datetime
import logging
import typing

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.agent.tasks.base as base
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.schemas
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "StatusReportInputs",
    "build_status_report",
    "StatusReportTask",
]


@dataclasses.dataclass(frozen=True)
class StatusReportInputs:
    """Everything build_status_report() needs, gathered by the caller.

    Assembled fresh (by Agent, from its own live state and a handful
    of async reads) right before every report is built, so this module
    stays ignorant of Agent internals."""

    utcnow: datetime.datetime
    supervisor_passphrase: str | None
    domain: str | None
    abitti2_version: str | None
    cert: dict[str, typing.Any] | None
    current_exam_package: dict[str, typing.Any] | None
    next_exam_packages: list[dict[str, typing.Any]] | None
    exam_stats: list[dict[str, typing.Any]] | None
    ktp_controller_stats: dict[str, typing.Any] | None
    cached_files: typing.Any
    answer_count: int | None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None
    last_message_from_abitti2_received_at: datetime.datetime | None
    exams: list[dict[str, typing.Any]] | None
    students: list[dict[str, typing.Any]] | None
    settings: dict[str, typing.Any]
    started_at: datetime.datetime | None
    is_auto_control_enabled: bool
    os_stats: dict[str, typing.Any]
    os_release: str
    puavo_os_image_name: str | None
    puavo_os_image_release: str | None


def build_status_report(inputs: StatusReportInputs) -> dict[str, typing.Any]:
    """Pure function, independently unit-testable: no I/O, no Agent state."""
    return {
        "created_at": inputs.utcnow,
        "abitti2": {
            "stats": {
                "exams": inputs.exam_stats,
            },
            "answer_count": inputs.answer_count,
            "domain": inputs.domain,
            "student_access_code": inputs.student_access_code,
            "supervisor_username": ktp_controller.abitti2.client.ABITTI2_SUPERVISOR_USERNAME,
            "supervisor_passphrase": inputs.supervisor_passphrase,
            "version": inputs.abitti2_version,
            "last_message_received_at": inputs.last_message_from_abitti2_received_at,
            "cert": inputs.cert,
            "exams": inputs.exams,
            "students": inputs.students,
        },
        "ktp_controller": {
            "settings": inputs.settings,
            "started_at": inputs.started_at,
            "is_auto_control_enabled": inputs.is_auto_control_enabled,
            "cached_files": inputs.cached_files,
            "current_exam_package": inputs.current_exam_package,
            "next_exam_packages": inputs.next_exam_packages,
            "stats": inputs.ktp_controller_stats,
        },
        "os": {
            "stats": inputs.os_stats,
            "release": inputs.os_release,
            "puavo_os_image_name": inputs.puavo_os_image_name,
            "puavo_os_image_release": inputs.puavo_os_image_release,
        },
    }


class StatusReportTask:
    """Fire-and-forget "create a status report" task, built on DirtySignal.

    mark_dirty() is the producer API for every trigger source (API
    commands, exam-package state changes, Abitti2 message handlers):
    none of them wait for the report to actually be built, so unlike
    RefreshExamsTask/StudentAccessCodeTask this isn't a
    CoalescingQueue-based request/response task.

    This is also the single owner of "the last report built": its
    result is read back by other Agent logic (the exam-package state
    machine), not just sent off, so it's exposed via get_last_report()/
    has_last_report_expired()/mark_expired() instead of being kept
    private the way RefreshExamsTask's output is.

    run_consumer() must be scheduled as its own asyncio task.
    """

    def __init__(
        self,
        *,
        min_examomatic_interval_sec: int,
        build_inputs: typing.Callable[[], typing.Awaitable[StatusReportInputs]],
    ) -> None:
        self.__min_examomatic_interval_sec = min_examomatic_interval_sec
        self.__build_inputs = build_inputs
        self.__signal = base.DirtySignal()
        self.__last_sent_to_examomatic_at: datetime.datetime | None = None
        self.__last_report: dict[str, typing.Any] | None = None
        self.__has_last_report_expired = False

    def mark_dirty(self) -> None:
        """Producer API for every trigger source."""
        self.__signal.mark_dirty()

    def get_last_report(self) -> dict[str, typing.Any] | None:
        return self.__last_report

    def has_last_report_expired(self) -> bool:
        return self.__has_last_report_expired

    def mark_expired(self) -> None:
        """Called by Agent when it discovers the last report's view of
        student sessions is stale (e.g. after a failed
        end-student-exam attempt), so it won't be relied on again
        until a fresh report is built."""
        self.__has_last_report_expired = True

    def __seconds_until_next_examomatic_send(
        self, *, utcnow: datetime.datetime | None = None
    ) -> float:
        if utcnow is None:
            utcnow = ktp_controller.utils.utcnow()

        if self.__last_sent_to_examomatic_at is None:
            return 0

        return (
            self.__min_examomatic_interval_sec
            - (utcnow - self.__last_sent_to_examomatic_at).total_seconds()
        )

    async def run_consumer(self) -> None:
        async with base.task_guard("create status reports"):
            while not base.SHUTDOWN_EVENT.is_set():
                await self.__signal.wait_dirty_or_timeout(
                    self.__seconds_until_next_examomatic_send()
                )

                inputs = await self.__build_inputs()
                status_report = build_status_report(inputs)

                try:
                    if (
                        self.__seconds_until_next_examomatic_send(utcnow=inputs.utcnow)
                        <= 0
                    ):
                        await ktp_controller.examomatic.client.send_status_report(
                            status_report
                        )
                        status_report["reported_at"] = inputs.utcnow
                        self.__last_sent_to_examomatic_at = inputs.utcnow
                        _LOGGER.debug("sent status report to Exam-O-Matic")
                except Exception:
                    _LOGGER.exception("failed to send status report to Exam-O-Matic")
                status_report.setdefault("reported_at", None)

                await ktp_controller.api.client.save_status_report(status_report)
                self.__last_report = status_report
                self.__has_last_report_expired = False
                _LOGGER.debug("sent status report to KTP Controller API")
