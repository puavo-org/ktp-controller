# Standard library imports
import datetime
import logging

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.agent.tasks.base as base
import ktp_controller.utils
from ktp_controller import SETTINGS

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "StudentAccessCodeTask",
]


_COOLDOWN_SEC = 60


async def _change_student_access_code(old_security_code: dict[str, str] | None) -> None:
    if old_security_code:
        _LOGGER.info(
            "Requesting Abitti2 to change student access code to ensure students "
            "cannot access exams with code (%r).",
            old_security_code,
        )
    else:
        _LOGGER.info("Requesting Abitti2 to change student access code.")
    await ktp_controller.abitti2.client.change_student_access_code()


class StudentAccessCodeTask:
    """Producer/consumer wrapper around changing the student access code.

    request_change() is the producer API for the CHANGE_STUDENT_ACCESS_CODE
    command handler (both direct and Exam-O-Matic-triggered loopback calls)
    and for ensure_code_changed()'s own use. At most one change is in
    flight and at most one more is guaranteed to run right after it, no
    matter how many callers are waiting (see
    ktp_controller.agent.tasks.base.CoalescingQueue). On top of that
    coalescing, a batch that would run within _COOLDOWN_SEC of the
    previously *executed* batch is resolved with False without calling
    Abitti2 at all, to avoid hammering it with change requests.

    run_consumer() must be scheduled as its own asyncio task.
    """

    def __init__(self) -> None:
        self.__queue: base.CoalescingQueue[None, bool] = base.CoalescingQueue()
        self.__last_change_at: datetime.datetime | None = None
        self.__old_security_code: dict[str, str] | None = None

    async def request_change(self) -> bool:
        """Producer API.

        Returns once a batch servicing this request (an already
        pending/in-flight batch, or a fresh one) has been resolved.
        """
        return await self.__queue.request(None)

    async def ensure_code_changed(
        self,
        *,
        auto_control_enabled: bool,
        last_received_security_code: dict[str, str] | None,
    ) -> bool:
        """Snapshot the current code, request a change, then keep
        returning False until Abitti2 reports a code different from the
        snapshot."""
        if not auto_control_enabled:
            return True  # We are never going to change it, so we are done.

        if not SETTINGS.abitti2_change_student_access_code_automatically:
            return True  # We are never going to change it, so we are done.

        if last_received_security_code is None:
            return False  # No point to change until we know what the current is.

        if self.__old_security_code is None:
            self.__old_security_code = last_received_security_code

        if self.__old_security_code == last_received_security_code:
            await self.request_change()
            _LOGGER.info(
                "Waiting until student access code has changed to ensure students "
                "cannot access exams with code (%r).",
                self.__old_security_code,
            )
            return False

        _LOGGER.info(
            "Access code has changed (%r => %r).",
            self.__old_security_code,
            last_received_security_code,
        )

        self.__old_security_code = None

        return True

    async def run_consumer(self) -> None:
        async with base.task_guard("student access code change consumer"):
            while not base.SHUTDOWN_EVENT.is_set():
                batch = await self.__queue.consume()
                futures = [future for _, future in batch]

                utcnow = ktp_controller.utils.utcnow()
                if self.__last_change_at is not None:
                    seconds_since_last_change = (
                        utcnow - self.__last_change_at
                    ).total_seconds()
                else:
                    seconds_since_last_change = None

                if (
                    seconds_since_last_change is not None
                    and seconds_since_last_change < _COOLDOWN_SEC
                ):
                    _LOGGER.warning(
                        "NOT requesting Abitti2 to change student access code, "
                        "because it was requested %d seconds ago. It can be "
                        "requested at most once per minute.",
                        int(seconds_since_last_change),
                    )
                    base.resolve_all(futures, False)
                    continue

                try:
                    await _change_student_access_code(self.__old_security_code)
                except Exception as exc:
                    base.reject_all(futures, exc)
                else:
                    self.__last_change_at = utcnow
                    base.resolve_all(futures, True)

    def reset(self) -> None:
        self.__old_security_code = None
