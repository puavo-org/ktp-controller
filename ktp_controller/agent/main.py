# Standard library imports
import argparse
import asyncio
import collections
import contextlib
import datetime
import enum
import json
import logging
import os
import os.path
import pathlib
import signal
import statistics
import sys
import time
import typing

# Third-party imports
import httpx
import pydantic
import websockets

import ktp_controller.abitti2.client
import ktp_controller.abitti2.naksu2
import ktp_controller.abitti2.schemas
import ktp_controller.abitti2.utils
import ktp_controller.agent
import ktp_controller.agent.answers
import ktp_controller.agent.exam_package
import ktp_controller.agent.state
import ktp_controller.agent.stats
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.messages
import ktp_controller.os
import ktp_controller.pydantic
import ktp_controller.schemas
import ktp_controller.utils

# Internal imports
from ktp_controller import SETTINGS, VERSION

_LOGGER = logging.getLogger(__name__)

_SHUTDOWN_EVENT = asyncio.Event()


@contextlib.asynccontextmanager
async def _task(
    name: str, *, on_exit_coro: typing.Awaitable[typing.Any] | None = None
) -> typing.AsyncIterator[None]:
    try:
        _LOGGER.info("Starting task %r...", name)
        yield
    except asyncio.CancelledError as err:
        if _SHUTDOWN_EVENT.is_set():
            # That's normal, the task was cancelled while the agent is shutting down.
            raise
        raise _UnexpectedCancel(f"Unexpected cancellation of task {name!r}!") from err
    finally:
        if _SHUTDOWN_EVENT.is_set():
            _LOGGER.info("Task %r was shut down.", name)
        else:
            _LOGGER.warning("Task %r was aborted!", name)
        if on_exit_coro is not None:
            await on_exit_coro


class Trigger(enum.StrEnum):
    TIME = "time"
    MANUAL_PREPARE = "manual_prepare"
    MANUAL_START = "manual_start"
    MANUAL_STOP = "manual_stop"
    MANUAL_ARCHIVE = "manual_archive"

    def __str__(self) -> str:
        return self.value


class Component(enum.StrEnum):
    API = "API"
    EXAMOMATIC = "Exam-O-Matic"
    ABITTI2 = "Abitti2"

    def __str__(self) -> str:
        return self.value


class _UnexpectedCancel(Exception):
    pass


class _StateTransition(typing.TypedDict):
    valid_triggers: tuple[Trigger, ...]
    time_condition: bool
    action: typing.Callable[[dict[str, typing.Any]], typing.Awaitable[bool]] | None
    next_state: str


def _simplify_exam_package(
    exam_package: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    return {
        "uuid": exam_package["external_id"],
        "scheduled_lock_time": exam_package["lock_time"],
        "scheduled_start_time": exam_package["start_time"],
        "scheduled_end_time": exam_package["end_time"],
        "state": exam_package["state"],
        "state_changed_at": exam_package["state_changed_at"],
        "started_at": exam_package["started_at"],
        "archived_at": exam_package["archived_at"],
    }


class Agent:
    def __init__(
        self,
        *,
        approx_api_ping_interval_sec: int = 5,
        approx_api_status_report_interval_sec: int = 30,
        approx_examomatic_ping_interval_sec: int = SETTINGS.examomatic_ping_interval_sec,
        approx_examomatic_min_status_report_interval_sec: int = SETTINGS.examomatic_min_status_report_interval_sec,
        approx_reconnect_timeout_sec: int = 5,
        approx_answers_download_interval_sec: int = SETTINGS.answer_transfer_interval_sec,
        approx_refresh_exams_interval_sec: int = SETTINGS.refresh_exams_interval_sec,
        state: ktp_controller.agent.state.AgentState,
        is_testbed_mode: bool = False,
    ):
        self.__is_testbed_mode = is_testbed_mode
        self.__do_crash = False
        self.__started_at: datetime.datetime | None = None
        self.__state = state
        self.__nonfinal_answers_download_task: asyncio.Task[None] | None = None
        self.__refresh_exams_lock = asyncio.Lock()
        self.__work_on_current_exam_package_lock = asyncio.Lock()
        self.__last_status_report_sent_to_examomatic_at: datetime.datetime | None = None
        self.__cached_list_of_locked_exam_packages: (
            list[dict[str, typing.Any]] | None
        ) = None
        self.__cached_abitti2_version: str | None = None

        self.__os_release = ktp_controller.os.get_release()

        self.__approx_api_ping_interval_sec = approx_api_ping_interval_sec
        self.__approx_api_status_report_interval_sec = (
            approx_api_status_report_interval_sec
        )
        self.__approx_examomatic_ping_interval_sec = approx_examomatic_ping_interval_sec
        self.__approx_examomatic_min_status_report_interval_sec = (
            approx_examomatic_min_status_report_interval_sec
        )
        self.__approx_reconnect_timeout_sec = approx_reconnect_timeout_sec
        self.__approx_answers_download_interval_sec = (
            approx_answers_download_interval_sec
        )
        self.__approx_refresh_exams_interval_sec = approx_refresh_exams_interval_sec

        # Abitti2 reports these
        self.__last_received_exam_list: list[dict[str, typing.Any]] | None = None
        self.__last_received_security_code: dict[str, str] | None = None
        self.__old_security_code: dict[str, str] | None = None
        self.__uploaded = False
        self.__last_message_from_abitti2_received_at: datetime.datetime | None = None
        self.__last_received_students: list[dict[str, typing.Any]] | None = None
        self.__last_received_answer_count: int | None = None
        self.__last_cold_reset_time: datetime.datetime | None = None

        self.__prev_connection_durations: collections.defaultdict[
            Component, list[float]
        ] = collections.defaultdict(list)
        self.__connection_stats: dict[
            Component,
            ktp_controller.agent.stats.ConnectionStats,
        ] = {}
        self.__commands = {
            str(
                ktp_controller.messages.Command.ENABLE_AUTO_CONTROL
            ): self.__command_enable_auto_control,
            str(
                ktp_controller.messages.Command.DISABLE_AUTO_CONTROL
            ): self.__command_disable_auto_control,
            str(
                ktp_controller.messages.Command.STOP_CURRENT_EXAM_PACKAGE
            ): self.__command_change_current_exam_package_state,
            str(
                ktp_controller.messages.Command.START_CURRENT_EXAM_PACKAGE
            ): self.__command_change_current_exam_package_state,
            str(
                ktp_controller.messages.Command.ARCHIVE_CURRENT_EXAM_PACKAGE
            ): self.__command_change_current_exam_package_state,
            str(
                ktp_controller.messages.Command.PREPARE_CURRENT_EXAM_PACKAGE
            ): self.__command_change_current_exam_package_state,
            str(ktp_controller.messages.Command.CRASH_AGENT): self.__command_crash,
        }

    @property
    def __is_auto_control_enabled(self) -> bool:
        return self.__state.is_auto_control_enabled

    @__is_auto_control_enabled.setter
    def __is_auto_control_enabled(self, value: bool) -> None:
        self.__state.is_auto_control_enabled = value

    def __set_auto_control(
        self,
        command_uuid: pydantic.UUID4,
        enabled: bool,
    ) -> ktp_controller.messages.CommandResultData:
        changed = enabled is not self.__is_auto_control_enabled

        self.__is_auto_control_enabled = enabled
        if changed:
            _LOGGER.info(
                "Auto control is now %s.", "enabled" if enabled else "disabled"
            )
            command_status = ktp_controller.messages.CommandStatus.OK
        else:
            command_status = ktp_controller.messages.CommandStatus.OK_NO_CHANGE

        return ktp_controller.messages.CommandResultData(
            command_uuid=command_uuid, command_status=command_status
        )

    async def __command_crash(
        self,
        command_uuid: pydantic.UUID4,
        command_data: ktp_controller.messages.CommandData,
    ) -> ktp_controller.messages.CommandResultData:
        if self.__is_testbed_mode:
            self.__do_crash = True
            return ktp_controller.messages.CommandResultData(
                command_uuid=command_uuid,
                command_status=ktp_controller.messages.CommandStatus.OK,
            )
        return ktp_controller.messages.CommandResultData(
            command_uuid=command_uuid,
            command_status=ktp_controller.messages.CommandStatus.ERROR,
            error_message="agent is not running in testbed mode",
        )

    async def __command_enable_auto_control(
        self,
        command_uuid: pydantic.UUID4,
        command_data: ktp_controller.messages.CommandData,
    ) -> ktp_controller.messages.CommandResultData:
        return self.__set_auto_control(command_uuid, True)

    async def __command_disable_auto_control(
        self,
        command_uuid: pydantic.UUID4,
        command_data: ktp_controller.messages.CommandData,
    ) -> ktp_controller.messages.CommandResultData:
        return self.__set_auto_control(command_uuid, False)

    async def __command_change_current_exam_package_state(
        self,
        command_uuid: pydantic.UUID4,
        command_data: ktp_controller.messages.CommandData,
    ) -> ktp_controller.messages.CommandResultData:
        if self.__is_auto_control_enabled:
            return ktp_controller.messages.CommandResultData(
                command_uuid=command_uuid,
                command_status=ktp_controller.messages.CommandStatus.ERROR,
                error_message=(
                    "the state of the current exam package cannot be "
                    "changed manually when auto control is enabled"
                ),
            )

        manual_trigger = {
            ktp_controller.messages.Command.ARCHIVE_CURRENT_EXAM_PACKAGE: Trigger.MANUAL_ARCHIVE,
            ktp_controller.messages.Command.PREPARE_CURRENT_EXAM_PACKAGE: Trigger.MANUAL_PREPARE,
            ktp_controller.messages.Command.START_CURRENT_EXAM_PACKAGE: Trigger.MANUAL_START,
            ktp_controller.messages.Command.STOP_CURRENT_EXAM_PACKAGE: Trigger.MANUAL_STOP,
        }[command_data.command]

        try:
            changed = await self.__work_on_current_exam_package(trigger=manual_trigger)
        except Exception as exception:
            return ktp_controller.messages.CommandResultData(
                command_uuid=command_uuid,
                command_status=ktp_controller.messages.CommandStatus.ERROR,
                error_message=str(exception),
            )

        if changed:
            command_status = ktp_controller.messages.CommandStatus.OK
        else:
            command_status = ktp_controller.messages.CommandStatus.OK_NO_CHANGE

        return ktp_controller.messages.CommandResultData(
            command_uuid=command_uuid, command_status=command_status
        )

    async def __prepare_current_exam_package(
        self,
        current_exam_package: dict[str, typing.Any],
    ) -> bool:
        _LOGGER.info("Preparing exam package: %r", current_exam_package)

        if not self.__uploaded:
            (
                exam_package_filepath,
                decrypt_codes,
            ) = await ktp_controller.agent.exam_package.create_exam_package_file(
                current_exam_package
            )

            exam_filenames = await ktp_controller.abitti2.client.prepare_exam_package(
                exam_package_filepath, decrypt_codes
            )

            _LOGGER.info(
                "Uploaded and decrypted %d exams from current exam package %r.",
                len(exam_filenames),
                current_exam_package["external_id"],
            )
        self.__uploaded = True

        if (
            self.__is_auto_control_enabled
            and SETTINGS.abitti2_change_student_access_code_automatically
        ):
            if self.__old_security_code is None:
                self.__old_security_code = self.__last_received_security_code
                _LOGGER.info(
                    "Requesting Abitti2 to change the access code to ensure students "
                    "cannot access new exams with the old code (%r).",
                    self.__old_security_code,
                )
                await ktp_controller.abitti2.client.change_student_access_code()
                return False

            if self.__old_security_code == self.__last_received_security_code:
                _LOGGER.info(
                    "Waiting until access code has changed to ensure students "
                    "cannot access new exams with the old code."
                )
                # Waiting until the security code is changed.
                return False

            _LOGGER.info(
                "Access code has changed (%r => %r), continue starting the exam package.",
                self.__old_security_code,
                self.__last_received_security_code,
            )

            _LOGGER.info(
                "API says the access code is: %r",
                await ktp_controller.api.client.get_student_access_code(),
            )

        self.__old_security_code = None

        _LOGGER.info(
            "Prepared current exam package %r successfully.",
            current_exam_package["external_id"],
        )

        self.__uploaded = False

        return True

    def __ensure_nonfinal_answers_download_task_is_running(
        self, current_exam_package: dict[str, typing.Any]
    ) -> None:
        if self.__nonfinal_answers_download_task is None:
            self.__nonfinal_answers_download_task = asyncio.create_task(
                self.__download_nonfinal_answers(current_exam_package)
            )
            _LOGGER.info(
                "Started periodic (approx. once per %d seconds) non-final answers download task.",
                self.__approx_answers_download_interval_sec,
            )

    async def __stop_nonfinal_answers_download_task(
        self, current_exam_package: dict[str, typing.Any]
    ) -> None:
        if self.__nonfinal_answers_download_task is None:
            _LOGGER.info("Periodic non-final answers download task is not running.")
            return

        _LOGGER.info("Stopping periodic non-final answers download task...")

        self.__nonfinal_answers_download_task.cancel()

        try:
            # _UnexpectedCancel is expected here because we explicitly
            # cancel the task. This is special case, all other tasks
            # are expected to not be canceled unless shutdown is in
            # progress.
            with contextlib.suppress(asyncio.CancelledError, _UnexpectedCancel):
                await self.__nonfinal_answers_download_task
        except Exception:
            _LOGGER.exception("Periodic non-final answers download task failed")
        finally:
            _LOGGER.info("Stopped periodic non-final answers download task.")
            self.__nonfinal_answers_download_task = None

    async def __start_current_exam_package(
        self,
        current_exam_package: dict[str, typing.Any],
    ) -> bool:
        _LOGGER.info("Starting exam package: %r", current_exam_package)
        await ktp_controller.abitti2.client.start_decrypted_exams()
        _LOGGER.info(
            "Started current exam package %r successfully.",
            current_exam_package["external_id"],
        )

        return True

    async def __start_stopping_current_exam_package(
        self, current_exam_package: dict[str, typing.Any]
    ) -> bool:
        _LOGGER.info(
            "Stopping current exam package %r...",
            current_exam_package["external_id"],
        )
        await self.__stop_current_exam_package(current_exam_package)
        return True  # Always proceed to the next state, we have started to stop the current exam.

    async def __stop_current_exam_package(
        self,
        current_exam_package: dict[str, typing.Any],
    ) -> bool:
        if (
            self.__is_auto_control_enabled
            and SETTINGS.abitti2_change_student_access_code_automatically
        ):
            # Change the security code first to ensure students cannot enter anymore.
            await ktp_controller.abitti2.client.change_student_access_code()

        last_status_report = await ktp_controller.api.client.get_last_status_report()
        if last_status_report is None:
            return False

        for student in last_status_report["abitti2"]["students"]:
            await ktp_controller.abitti2.client.stop_exam_session(
                student["session_uuid"]
            )

        is_stopped = (
            ktp_controller.abitti2.utils.no_active_students(last_status_report)
            and current_exam_package["state"] == "stopping"
            and last_status_report["created_at"]
            > current_exam_package["state_changed_at"]
        )

        if is_stopped:
            _LOGGER.info(
                "Stopped current exam package %r successfully.",
                current_exam_package["external_id"],
            )
        else:
            _LOGGER.info(
                "Stopping current exam package %r ...",
                current_exam_package["external_id"],
            )

        return is_stopped

    async def __archive_current_exam_package(
        self,
        current_exam_package: dict[str, typing.Any],
    ) -> bool:
        _LOGGER.info(
            "Archiving current exam package %r...",
            current_exam_package["external_id"],
        )
        await self.__stop_nonfinal_answers_download_task(current_exam_package)
        await self.__download_answers(
            current_exam_package, is_final=ktp_controller.examomatic.client.IsFinal.TRUE
        )
        await ktp_controller.abitti2.client.reset()
        _LOGGER.info(
            "Archived current exam package %r successfully.",
            current_exam_package["external_id"],
        )
        return True

    async def __download_answers(
        self,
        current_exam_package: dict[str, typing.Any],
        is_final: ktp_controller.examomatic.client.IsFinal,
    ) -> None:
        is_final = ktp_controller.examomatic.client.IsFinal(is_final)
        status_report = await ktp_controller.api.client.get_last_status_report()
        if status_report is None or status_report["abitti2"]["answer_count"] is None:
            _LOGGER.warning(
                "I don't know yet if there are answers to download, "
                "but I won't take the risk of trying to download them from Abitti2, "
                "because Abitti2 can block indefinitely if there are no answers."
            )
            return
        if status_report["abitti2"]["answer_count"] > 0:
            await ktp_controller.agent.answers.download_answers_file(
                exam_package_external_id=current_exam_package["external_id"],
                is_final=is_final,
            )
        else:
            # If there are no answers, Abitti2 blocks download
            # requests indefinitely.
            _LOGGER.warning("There are no answers to download.")

    async def __download_nonfinal_answers(
        self, current_exam_package: dict[str, typing.Any]
    ) -> None:
        started = False
        async with _task("periodic non-final answers download"):
            while not _SHUTDOWN_EVENT.is_set():
                try:
                    if started:
                        await asyncio.sleep(self.__approx_answers_download_interval_sec)
                    started = True
                    await self.__download_answers(
                        current_exam_package,
                        is_final=ktp_controller.examomatic.client.IsFinal.FALSE,
                    )
                except Exception:
                    _LOGGER.exception(
                        "Failed to download non-final answers from Abitti2."
                    )

    async def __work_on_current_exam_package(self, *, trigger: Trigger) -> bool:
        trigger = Trigger(trigger)  # Raises ValueError if trigger is not a Trigger.
        if (
            trigger == Trigger.TIME
            and self.__work_on_current_exam_package_lock.locked()
        ):
            return False
        async with self.__work_on_current_exam_package_lock:
            return await self.__work_on_current_exam_package_locked(trigger=trigger)

    async def __work_on_current_exam_package_locked(self, *, trigger: Trigger) -> bool:
        _LOGGER.info("Working on the current exam package.")
        utcnow = ktp_controller.utils.utcnow()

        if self.__do_crash:
            _LOGGER.fatal("CRASH!")
            sys.exit(1)

        if trigger.startswith("manual_") and self.__is_auto_control_enabled:
            raise RuntimeError(
                "Critical internal logic error!. "
                "Auto control is enabled and manual trigger encountered. "
                "This is an usage error which should have been properly handled "
                "and reported by upper levels in the call stack."
            )

        locked_exam_packages = await self.__get_locked_exam_packages()

        if len(locked_exam_packages) == 0:
            if self.__is_auto_control_enabled and self.__last_received_exam_list == []:  # noqa: SIM102
                # Cold reset: Abitti2 is not reporting it has any
                # exams running, which means it has just
                # started. So, we always want to have at least
                # waiting lobby exam running there. But sometimes
                # Abitti2 is really slow to get it up and running,
                # so, we have a short 15 waiting period here to
                # not flood Abitti2 with consecutive reset
                # requests.
                if (
                    self.__last_cold_reset_time is None
                    or (utcnow - self.__last_cold_reset_time).total_seconds() >= 15
                ):
                    await ktp_controller.abitti2.client.reset()
                    self.__last_cold_reset_time = utcnow
            return False  # No current exam package

        current_exam_package = locked_exam_packages[0]

        if not current_exam_package["locked"]:
            raise RuntimeError(
                "Critical internal logic error! "
                "The current exam package is not locked! "
                "It should be impossible, because the definition "
                "of current implies locked.",
                current_exam_package,
            )

        status_report = await ktp_controller.api.client.get_last_status_report()
        if status_report is None:
            _LOGGER.warning(
                "Status of the whole system is still partially unknown, not processing"
                " exam packages until a complete view of the current status is formed."
            )
            return False

        _LOGGER.debug(
            "Triggered by %s, working on the current exam package: %s",
            trigger,
            current_exam_package,
        )

        changed = False

        state_transitions: dict[str | None, _StateTransition] = {
            None: {
                "valid_triggers": (Trigger.MANUAL_PREPARE, Trigger.TIME),
                "time_condition": self.__is_auto_control_enabled,
                "action": self.__prepare_current_exam_package,
                "next_state": "ready",
            },
            "ready": {
                "valid_triggers": (Trigger.MANUAL_START, Trigger.TIME),
                "time_condition": (
                    self.__is_auto_control_enabled
                    and (
                        utcnow
                        >= datetime.datetime.fromisoformat(
                            current_exam_package["start_time"]
                        )
                    )
                ),
                "action": self.__start_current_exam_package,
                "next_state": "running",
            },
            "running": {
                "valid_triggers": (Trigger.MANUAL_STOP, Trigger.TIME),
                "time_condition": (
                    self.__is_auto_control_enabled
                    and (
                        utcnow
                        >= datetime.datetime.fromisoformat(
                            current_exam_package["end_time"]
                        )
                    )
                    and (
                        ktp_controller.abitti2.utils.no_active_students(status_report)
                        or len(locked_exam_packages) > 1
                    )
                ),
                "action": self.__start_stopping_current_exam_package,
                "next_state": "stopping",
            },
            "stopping": {
                "valid_triggers": (Trigger.MANUAL_STOP, Trigger.TIME),
                # We already stopping, so regardless of the auto
                # control state, we call the stop function until it
                # reports that everything has stopped.
                "time_condition": True,
                "action": self.__stop_current_exam_package,
                "next_state": "stopped",
            },
            "stopped": {
                "valid_triggers": (Trigger.MANUAL_ARCHIVE, Trigger.TIME),
                "time_condition": self.__is_auto_control_enabled,
                "action": self.__archive_current_exam_package,
                "next_state": "archived",
            },
            "archived": {
                "valid_triggers": (Trigger.TIME,),
                "time_condition": True,
                "action": None,
                "next_state": "archived",
            },
        }

        state = current_exam_package["state"]
        if state == "running":
            self.__ensure_nonfinal_answers_download_task_is_running(
                current_exam_package
            )

        transition = state_transitions[state]

        if trigger not in transition["valid_triggers"]:
            raise ktp_controller.agent.exam_package.ExamPackageUsageError(
                f"trigger '{trigger}' is not applicable for the current exam package in state '{state}'"
            )

        if trigger != Trigger.TIME or transition["time_condition"]:
            action = transition["action"]
            _LOGGER.debug(
                "Doing transition from %s to %s, triggered by %s (time_condition=%s). Action is %s",
                state,
                transition["next_state"],
                trigger,
                transition["time_condition"],
                action,
            )
            if action is None:
                do_transition = True
            else:
                do_transition = await action(current_exam_package)
            if do_transition:
                changed = await ktp_controller.agent.exam_package.set_current_exam_package_state(
                    current_exam_package, transition["next_state"]
                )

        if changed:
            _LOGGER.info(
                "State of the current exam package changed from %s to %s",
                state,
                transition["next_state"],
            )
        else:
            _LOGGER.debug(
                "State of the current exam package did not change. It is %s.",
                state,
            )

        return changed

    async def __send_pings_to_api(self, websock: websockets.ClientConnection) -> None:
        async with _task("periodic ping-pong with API"):
            while not _SHUTDOWN_EVENT.is_set():
                message = ktp_controller.messages.PingMessage().model_dump_json()
                await websock.send(message)
                _LOGGER.debug("--> API: %s", message)
                await asyncio.sleep(self.__approx_api_ping_interval_sec)

    async def __send_status_reports_to_api(
        self, websock: websockets.ClientConnection
    ) -> None:
        async with _task("periodic status reporting to API"):
            while not _SHUTDOWN_EVENT.is_set():
                message = ktp_controller.messages.StatusReportMessage(
                    data=ktp_controller.messages.StatusReportData(
                        is_auto_control_enabled=self.__is_auto_control_enabled
                    ),
                ).model_dump_json()
                await websock.send(message)
                _LOGGER.debug("--> API: %s", message)
                await asyncio.sleep(self.__approx_api_status_report_interval_sec)

    async def __send_pings_to_examomatic(
        self, websock: websockets.ClientConnection
    ) -> None:
        async with _task("periodic ping-pong with Exam-O-Matic"):
            while not _SHUTDOWN_EVENT.is_set():
                message = json.dumps(
                    {
                        "type": "ping",
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
                await websock.send(message)
                _LOGGER.debug("--> Exam-O-Matic: %s", message)
                await asyncio.sleep(self.__approx_examomatic_ping_interval_sec)

    async def __communicate_with_api(
        self, websock: websockets.ClientConnection
    ) -> None:
        async with _task("communication with API"):
            async for data in websock:
                _LOGGER.debug("<-- API: %s", data)
                try:
                    message = ktp_controller.utils.json_loads_dict(data)
                except ValueError:
                    # Most probably a programming error, API should not
                    # send invalid JSON to agents.
                    _LOGGER.exception("API sent invalid JSON data!")
                    continue

                try:
                    message_kind = message["kind"]
                except KeyError:
                    _LOGGER.exception("API sent invalid message")
                    continue

                if message_kind == "command":
                    try:
                        command_data = (
                            ktp_controller.messages.CommandData.model_validate(
                                message["data"]
                            )
                        )
                    except pydantic.ValidationError:
                        _LOGGER.exception("API sent invalid command data")
                        command_result = ktp_controller.messages.CommandResultData(
                            command_uuid=message["uuid"],
                            command_status=ktp_controller.messages.CommandStatus.ERROR,
                            error_message="critical internal error",
                        )
                    else:
                        _LOGGER.info("Executing command %r...", command_data.command)
                        try:
                            command_result = await self.__commands[
                                command_data.command
                            ](message["uuid"], command_data)
                        except Exception:
                            _LOGGER.exception(
                                "Executing command %r failed", command_data.command
                            )
                            command_result = ktp_controller.messages.CommandResultData(
                                command_uuid=message["uuid"],
                                command_status=ktp_controller.messages.CommandStatus.ERROR,
                                error_message="critical internal error",
                            )
                        else:
                            _LOGGER.info(
                                "Executed command %r successfully.",
                                command_data.command,
                            )
                    await websock.send(
                        ktp_controller.messages.CommandResultMessage(
                            kind=ktp_controller.messages.MessageKind.COMMAND_RESULT,
                            data=command_result,
                        ).model_dump_json()
                    )
                    _LOGGER.info("Sent command result %r successfully.", command_result)
                    continue

                if message_kind == "pong":
                    # Whenever we get ponged, it's a sign for us to do
                    # some auto control work. So, keep ping pong interval
                    # quite short. This could be replaced with more
                    # sophisticated scheduling logic, but for now,
                    # ping-pong scheduling is good enough.
                    try:
                        await self.__work_on_current_exam_package(trigger=Trigger.TIME)
                    except Exception:
                        _LOGGER.exception(
                            "automatic work on the current exam package failed"
                        )
                    # Ping pong is a great game!
                    # Let's
                    continue  # playing it!

                _LOGGER.error("unknown API message kind: %s", message_kind)

    async def __communicate_with_examomatic(
        self, websock: websockets.ClientConnection
    ) -> None:
        async with _task("communication with Exam-O-Matic"):
            async for data in websock:
                received_at = ktp_controller.utils.utcnow()
                _LOGGER.debug("<-- Exam-O-Matic: %s", data)
                try:
                    message = ktp_controller.examomatic.client.websock_validate_message(
                        data
                    )
                except ValueError:
                    _LOGGER.exception(
                        "received invalid data from Exam-O-Matic: %r", data
                    )
                    continue

                examomatic_stats = typing.cast(
                    ktp_controller.agent.stats.ExamomaticConnectionStats,
                    self.__connection_stats[Component.EXAMOMATIC],
                )
                examomatic_stats.last_message_received_at = received_at

                if message["type"] == "pong":
                    _LOGGER.info("received pong message from Exam-O-Matic")
                    examomatic_stats.ping_pong_count += 1
                    continue  # pongs are not acked

                if message["type"] == "change_keycode":
                    _LOGGER.info("received change_keycode message from Exam-O-Matic")
                    if not self.__is_auto_control_enabled:
                        _LOGGER.error(
                            "Keycode cannot be changed by Exam-O-Matic, because auto control is not enabled."
                        )
                        continue
                    try:
                        await ktp_controller.abitti2.client.change_student_access_code()
                    except Exception:
                        _LOGGER.exception("Failed to changed student access code")
                        continue  # Failed requests are not acked
                    _LOGGER.info("Keycode changed.")
                elif message["type"] == "refresh_exams":
                    _LOGGER.info("received refresh_exams message from Exam-O-Matic")
                    try:
                        async with self.__refresh_exams_lock:
                            await self.__refresh_exams(is_spontaneous=False)
                    except Exception:
                        _LOGGER.exception("Failed to refresh exams")
                        continue  # Failed requests are not acked
                else:
                    _LOGGER.error(
                        "received message of unknown type %r from Exam-O-Matic",
                        message["type"],
                    )
                    continue  # Unknown requests are not acked

                await ktp_controller.examomatic.client.websock_ack(websock, message)

    async def __handle_abitti2_ping_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: dict[str, typing.Any] | None,
    ) -> None:
        await websock.send("pong")

    async def __handle_abitti2_security_code_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: dict[str, typing.Any],
    ) -> None:
        message_data = message["data"]
        try:
            security_code = message_data["securityCode"]
        except KeyError:
            # Security code is not always there. When security code
            # change is requested, Abitti2 (at least v1.18.0) seems to
            # send four security-code messages: first two are empty
            # and last two contain identical security codes.
            return

        try:
            ktp_controller.abitti2.utils.validate_security_code(security_code)
        except ValueError as value_error:
            _LOGGER.error(
                "received invalid security code from Abitti2: %s: %r",
                value_error,
                security_code,
            )
            return

        self.__last_received_security_code = security_code

        status_report = await ktp_controller.api.client.get_last_status_report()
        if status_report is None:
            return

        await self.__send_status_report()

    def __validate_abitti2_stats_message(self, message: dict[str, typing.Any]) -> bool:
        try:
            ktp_controller.abitti2.schemas.Abitti2StatsMessage.model_validate(message)
        except ValueError:
            _LOGGER.error(
                "received unexpected status message from Abitti2: %r", message
            )
            return False

        return True

    async def __handle_abitti2_stats_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: dict[str, typing.Any],
    ) -> None:
        ktp_controller.abitti2.utils.sanitize_stats_message(message)

        try:
            students = ktp_controller.abitti2.utils.parse_students(
                message, utcnow=received_at
            )
        except ValueError:
            _LOGGER.exception("Failed to parse students list received from Abitti2")
            self.__last_received_students = None
        else:
            self.__last_received_students = students
            if (
                self.__is_auto_control_enabled
                and SETTINGS.abitti2_allow_students_to_use_browsers
            ):
                await ktp_controller.abitti2.utils.allow_students_to_use_browsers(
                    students
                )

        self.__last_received_answer_count = message["data"]["answerPaperCount"]

        await self.__send_status_report()

    def __has_exam_stats(self) -> bool:
        # Stat calculation requires the information below. If any of
        # them are missing, we cannot calculate stats, i.e. there are
        # not stats available.
        if (
            self.__last_received_answer_count is None
            or self.__last_received_students is None
            or self.__last_received_exam_list is None
        ):
            return False

        # No exams, no stats.
        return len(self.__last_received_exam_list) != 0

    def __get_exam_stats(self) -> list[dict[str, typing.Any]] | None:
        if not self.__has_exam_stats():
            return None

        # __has_exam_stats() guarantees these are populated.
        assert self.__last_received_exam_list is not None
        assert self.__last_received_students is not None

        exam_stats = []
        for exam in self.__last_received_exam_list:
            exam_started_at = exam["started_at"]
            if exam_started_at is None:
                # Stats of unstarted exams are not interesting.
                continue
            exam_stats.append(
                {
                    "title": exam["title"],
                    "active_students_count": 0,
                    "finished_students_count": 0,
                    "flagged_students_count": 0,
                }
            )

        exam_stats_by_title = {entry["title"]: entry for entry in exam_stats}

        for student in self.__last_received_students:
            exam_title = student["exam_title"]
            if exam_title is not None:
                try:
                    stats = exam_stats_by_title[exam_title]
                except KeyError:
                    # Abitti2 reported a student with exam title which
                    # does not exist! So, we cannot give out reliable exam
                    # stats.
                    _LOGGER.error(
                        "Abitti2 reported there's a student in exam %r, but Abitti2 has NOT reported such exam actually exists!",
                        exam_title,
                    )
                    return None
            if student["has_finished"]:
                stats["finished_students_count"] += 1
            else:
                if len(student["flags"]) == 0:
                    stats["active_students_count"] += 1
                else:
                    stats["flagged_students_count"] += 1

        return exam_stats

    def __get_websocket_stats(
        self, component: Component, utcnow: datetime.datetime
    ) -> dict[str, typing.Any]:
        component = Component(component)

        try:
            stats = self.__connection_stats[component]
        except KeyError:
            connection_duration_current = None
            connection_duration_mean = None
            connection_duration_stdev = None
            connection_count = 0
        else:
            connection_duration_current = (utcnow - stats.connected_at).total_seconds()
            connection_durations = [
                connection_duration_current
            ] + self.__prev_connection_durations[component]
            connection_duration_mean = statistics.mean(connection_durations)
            if len(connection_durations) > 1:
                connection_duration_stdev = statistics.stdev(connection_durations)
            else:
                connection_duration_stdev = None
            connection_count = len(connection_durations)

        return {
            "connection_duration_current": connection_duration_current,
            "connection_duration_mean": connection_duration_mean,
            "connection_duration_stdev": connection_duration_stdev,
            "connection_count": connection_count,
        }

    def __get_stats(self) -> dict[str, typing.Any]:
        utcnow = ktp_controller.utils.utcnow()

        stats: dict[str, typing.Any] = {}

        for key_prefix, name in zip(
            ("abitti2", "api", "examomatic"),
            (Component.ABITTI2, Component.API, Component.EXAMOMATIC),
            strict=False,
        ):
            key = f"{key_prefix}_websocket_stats"
            stats[key] = self.__get_websocket_stats(name, utcnow)

        return stats

    async def __send_status_report(self) -> None:
        try:
            supervisor_passphrase = (
                ktp_controller.abitti2.naksu2.read_supervisor_passphrase()
            )
        except Exception:
            _LOGGER.exception("failed to read supervisor passphrase")
            supervisor_passphrase = None

        try:
            domain = ktp_controller.abitti2.naksu2.read_domain()
        except Exception:
            _LOGGER.exception("failed to read domain")
            domain = None

        try:
            abitti2_version = await self.__get_abitti2_version()
        except Exception:
            _LOGGER.exception("failed to get current Abitti2 version")
            abitti2_version = None

        try:
            locked_exam_packages = await self.__get_locked_exam_packages()
        except Exception:
            _LOGGER.exception("failed to get locked exam packages")
            current_exam_package = None
            next_exam_packages = None
        else:
            if len(locked_exam_packages) == 0:
                current_exam_package = None
                next_exam_packages = []
            else:
                current_exam_package = locked_exam_packages[0]
                next_exam_packages = locked_exam_packages[1:]

        if current_exam_package is not None:
            # Internal representation of the exam package is more
            # complex, here it's simplified for the status report.
            current_exam_package = _simplify_exam_package(current_exam_package)
            next_exam_packages = [_simplify_exam_package(p) for p in next_exam_packages]

        utcnow = ktp_controller.utils.utcnow()

        try:
            exam_stats = self.__get_exam_stats()
        except Exception:
            _LOGGER.exception("Failed to get exam stats")
            exam_stats = None

        try:
            ktp_controller_stats = self.__get_stats()
        except Exception:
            _LOGGER.exception("Failed to get KTP Controller stats")
            ktp_controller_stats = None

        cached_files = ktp_controller.files.get_cached_files()

        status_report: dict[str, typing.Any] = {
            "created_at": utcnow,
            "abitti2": {
                "stats": {
                    "exams": exam_stats,
                },
                "answer_count": self.__last_received_answer_count,
                "domain": domain,
                "student_access_code": ktp_controller.abitti2.utils.security_code_to_student_access_code(
                    self.__last_received_security_code
                ),
                "supervisor_username": ktp_controller.abitti2.client.ABITTI2_SUPERVISOR_USERNAME,
                "supervisor_passphrase": supervisor_passphrase,
                "version": abitti2_version,
                "last_message_received_at": self.__last_message_from_abitti2_received_at,
                "exams": self.__last_received_exam_list,
                "students": self.__last_received_students,
            },
            "ktp_controller": {
                "settings": SETTINGS.model_dump(),
                "started_at": self.__started_at,
                "is_auto_control_enabled": self.__is_auto_control_enabled,
                "cached_files": cached_files,
                "current_exam_package": current_exam_package,
                "next_exam_packages": next_exam_packages,
                "stats": ktp_controller_stats,
            },
            "os": {
                "stats": ktp_controller.os.get_stats(),
                "release": self.__os_release,
            },
        }

        try:
            if (
                self.__last_status_report_sent_to_examomatic_at is None
                or (
                    utcnow - self.__last_status_report_sent_to_examomatic_at
                ).total_seconds()
                > self.__approx_examomatic_min_status_report_interval_sec
            ):
                await ktp_controller.examomatic.client.send_status_report(status_report)
                status_report["reported_at"] = utcnow
                self.__last_status_report_sent_to_examomatic_at = utcnow
                _LOGGER.debug("sent status report to Exam-O-Matic")
        except Exception:
            _LOGGER.exception("failed to send status report to Exam-O-Matic")
        status_report.setdefault("reported_at", None)

        await ktp_controller.api.client.send_status_report(status_report)
        _LOGGER.debug("sent status report to KTP Controller API")

    async def __handle_abitti2_exams_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: dict[str, typing.Any],
    ) -> None:
        exam_list = []

        for abitti2_exam in message["data"]:
            if abitti2_exam["startTime"] is None:
                started_at = None
            else:
                started_at = ktp_controller.utils.strfdt(
                    datetime.datetime.fromisoformat(abitti2_exam["startTime"])
                )
            exam_list.append(
                {
                    "uuid": abitti2_exam["examUuid"],
                    "title": abitti2_exam["examTitle"],
                    "started_at": started_at,
                }
            )

        self.__last_received_exam_list = exam_list

    def __decode_abitti2_message(
        self, data: str | bytes
    ) -> tuple[str | None, dict[str, typing.Any] | None]:
        if data == "ping":
            return ("ping", None)

        try:
            message = ktp_controller.utils.json_loads_dict(data)
        except ValueError:
            _LOGGER.exception("received invalid JSON from Abitti2: %r", data)
            return (None, None)

        try:
            return (message["type"], message)
        except KeyError:
            _LOGGER.exception("received invalid message from Abitti2: %r", data)
            return (None, None)

    async def __clear_abitti2_caches(self) -> None:
        self.__cached_abitti2_version = None
        _LOGGER.info("All cached Abitti2 information has been cleared.")

    async def __communicate_with_abitti2(
        self, websock: websockets.ClientConnection
    ) -> None:
        async with _task(
            "communication with Abitti2", on_exit_coro=self.__clear_abitti2_caches()
        ):
            async for data in websock:
                received_at = ktp_controller.utils.utcnow()
                self.__last_message_from_abitti2_received_at = received_at

                _LOGGER.debug("<-- Abitti2: %s", data)

                message_type, message = self.__decode_abitti2_message(data)
                if message_type is None:
                    continue

                handlers: dict[
                    str,
                    typing.Callable[..., typing.Awaitable[None]] | None,
                ] = {
                    "ping": self.__handle_abitti2_ping_message,
                    "security-code": self.__handle_abitti2_security_code_message,
                    "stats": self.__handle_abitti2_stats_message,
                    "exams": self.__handle_abitti2_exams_message,
                    "servers": None,  # Simply ignored for now
                }
                try:
                    handler = handlers[message_type]
                except KeyError:
                    _LOGGER.warning(
                        "unhandled %r message from Abitti2: %r", message_type, message
                    )
                    continue

                _LOGGER.debug("received %r message from Abitti2", message_type)

                if handler is not None:
                    try:
                        await handler(websock, received_at, message)
                    except Exception:
                        _LOGGER.exception(
                            "failed to handle %r message from Abitti2: %r",
                            message_type,
                            message,
                        )

    async def __maintain_websocket_connection(
        self,
        name: Component,
        url: str,
        asyncfuncs: typing.Iterable[
            typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]
        ],
        *,
        connection_stats_class: type[ktp_controller.agent.stats.ConnectionStats],
        additional_headers: dict[str, str] | None = None,
        on_exit_coro: typing.Awaitable[typing.Any] | None = None,
    ) -> None:
        started = False
        async with _task(
            f"websocket maintenance to {name} ({url!r})", on_exit_coro=on_exit_coro
        ):
            while not _SHUTDOWN_EVENT.is_set():
                try:
                    if started:
                        _LOGGER.error(
                            "Reconnect to %s (%r) in approximately %d seconds...",
                            name,
                            url,
                            self.__approx_reconnect_timeout_sec,
                        )
                        await asyncio.sleep(self.__approx_reconnect_timeout_sec)
                    started = True
                    async with websockets.connect(
                        url,
                        additional_headers=additional_headers,
                    ) as websock:
                        self.__connection_stats[name] = connection_stats_class(
                            ktp_controller.utils.utcnow()
                        )
                        async with asyncio.TaskGroup() as tg:
                            for asyncfunc in asyncfuncs:
                                tg.create_task(asyncfunc(websock))
                except* _UnexpectedCancel:
                    raise
                except* Exception:
                    _LOGGER.exception("Websocket connection to %s has failed!", name)
                finally:
                    if name in self.__connection_stats:
                        _LOGGER.info("Websocket connection to %r was closed.", url)
                        self.__prev_connection_durations[name].append(
                            (
                                ktp_controller.utils.utcnow()
                                - self.__connection_stats[name].connected_at
                            ).total_seconds()
                        )
                    self.__connection_stats.pop(name, None)

    async def __maintain_websocket_connection_to_api(self) -> None:
        await self.__maintain_websocket_connection(
            Component.API,
            ktp_controller.api.client.get_agent_websock_url(),
            [
                self.__send_pings_to_api,
                self.__send_status_reports_to_api,
                self.__communicate_with_api,
            ],
            connection_stats_class=ktp_controller.agent.stats.APIConnectionStats,
        )

    async def __maintain_websocket_connection_to_examomatic(self) -> None:
        await self.__maintain_websocket_connection(
            Component.EXAMOMATIC,
            ktp_controller.examomatic.client.get_examomatic_websock_url(),
            [
                self.__send_pings_to_examomatic,
                self.__communicate_with_examomatic,
            ],
            connection_stats_class=ktp_controller.agent.stats.ExamomaticConnectionStats,
            additional_headers=ktp_controller.examomatic.client.get_basic_auth(),
        )

    async def __maintain_websocket_connection_to_abitti2(self) -> None:
        await self.__maintain_websocket_connection(
            Component.ABITTI2,
            ktp_controller.abitti2.client.get_abitti2_websock_url(),
            [
                self.__communicate_with_abitti2,
            ],
            connection_stats_class=ktp_controller.agent.stats.Abitti2ConnectionStats,
            additional_headers=ktp_controller.abitti2.client.get_basic_auth(),
            on_exit_coro=self.__clear_abitti2_caches(),
        )

    async def __ensure_exam_file_exists(
        self, eom_scheduled_exam: dict[str, typing.Any]
    ) -> None:
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

    async def __upload_answers_files(self) -> None:
        answers_file_dir_path = pathlib.Path(ktp_controller.files.ANSWERS_FILE_DIR)
        for answers_file_path in sorted(
            answers_file_dir_path.glob("*/*.meb"), key=lambda p: p.name
        ):
            uploaded = await ktp_controller.agent.answers.upload_answers_file(
                answers_file_path
            )
            if uploaded:
                # One at a time, this function will be called soon
                # again.
                break

    async def __get_abitti2_version(self) -> str:
        if self.__cached_abitti2_version is None:
            self.__cached_abitti2_version = (
                await ktp_controller.abitti2.client.get_current_abitti2_version()
            )
        return self.__cached_abitti2_version

    async def __get_locked_exam_packages(
        self,
    ) -> list[dict[str, typing.Any]]:
        async with self.__refresh_exams_lock:
            if self.__cached_list_of_locked_exam_packages is None:
                self.__cached_list_of_locked_exam_packages = (
                    await ktp_controller.api.client.get_locked_exam_packages()
                )
            return self.__cached_list_of_locked_exam_packages

    async def __refresh_exams(self, *, is_spontaneous: bool) -> None:
        _LOGGER.info(
            "Starting %sexam refresh...",
            "spontaneous " if is_spontaneous else "requested ",
        )

        try:
            eom_exam_info = await ktp_controller.examomatic.client.get_exam_info()
        except httpx.HTTPStatusError as http_error:
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
            await self.__ensure_exam_file_exists(eom_scheduled_exam)

        await ktp_controller.api.client.save_exam_info(eom_exam_info)
        # Invalidate cached list of locked exam packages. Next call to
        # self.__get_locked_exam_packages() will retrieve the updated
        # list.
        self.__cached_list_of_locked_exam_packages = None

        _LOGGER.info("refreshed exams successfully")

    async def __file_cleanup_task(self) -> None:
        started = False
        async with _task("file cleanup"):
            while not _SHUTDOWN_EVENT.is_set():
                try:
                    if started:
                        await asyncio.sleep(300)
                    started = True
                    await ktp_controller.files.cleanup_files(logger=_LOGGER)
                except Exception:
                    _LOGGER.exception("file cleanup failed")

    async def __answers_file_upload_task(self) -> None:
        started = False
        async with _task("answers file upload"):
            while not _SHUTDOWN_EVENT.is_set():
                try:
                    if started:
                        await asyncio.sleep(30)
                    started = True
                    await self.__upload_answers_files()
                except Exception:
                    _LOGGER.exception("answers file upload failed")

    async def __periodic_refresh_exams(self) -> None:
        started = False
        async with _task("periodic exam refresh"):
            while not _SHUTDOWN_EVENT.is_set():
                try:
                    if started:
                        await asyncio.sleep(self.__approx_refresh_exams_interval_sec)
                    started = True
                    async with self.__refresh_exams_lock:
                        await self.__refresh_exams(is_spontaneous=True)
                except Exception:
                    _LOGGER.exception("Failed to refresh exams")

    async def forever(self) -> None:
        _LOGGER.info("Started.")
        loop = asyncio.get_running_loop()
        main_task = asyncio.current_task()

        def trigger_shutdown(signum: signal.Signals) -> None:
            _LOGGER.info("Received signal %r, stopping...", signum)
            _SHUTDOWN_EVENT.set()
            if main_task is not None:
                main_task.cancel()

        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
            loop.add_signal_handler(sig, trigger_shutdown, sig)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.__maintain_websocket_connection_to_api())
                tg.create_task(self.__maintain_websocket_connection_to_abitti2())
                tg.create_task(self.__maintain_websocket_connection_to_examomatic())
                tg.create_task(self.__periodic_refresh_exams())
                tg.create_task(self.__answers_file_upload_task())
                tg.create_task(self.__file_cleanup_task())

                # Keep the main task alive while workers run
                await asyncio.Event().wait()
        except* asyncio.CancelledError:
            _LOGGER.info("Stopping all tasks...")
            try:
                # Give the tasks 5 seconds to run their 'finally' blocks
                await asyncio.wait_for(self.__cancel_all_tasks(), timeout=5.0)
            except TimeoutError:
                _LOGGER.error("Task cleanup exceeded timeout! Forcefully exiting.")
            _LOGGER.info("All tasks have been stopped.")
        except* Exception:
            _LOGGER.exception("Operational error!")
        finally:
            _LOGGER.info("Stopped.")

    async def __cancel_all_tasks(self) -> None:
        """Logic to ensure all pending tasks are accounted for."""
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        # Wait for all tasks to acknowledge cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

    def run(self) -> None:
        self.__started_at = ktp_controller.utils.utcnow()

        # ktp_controller.abitti2.client needs dummy exam package to reset Abitti2.
        ktp_controller.agent.exam_package.create_dummy_exam_package_file()

        with contextlib.suppress(asyncio.CancelledError):
            asyncio.run(self.forever())

    def get_state(self) -> ktp_controller.agent.state.AgentState:
        return self.__state.model_copy()


def _run(args: argparse.Namespace) -> int:
    utcnow = ktp_controller.utils.utcnow()

    if ktp_controller.utils.is_puavo_os():
        try:
            ktp_controller.files.create_user_friendly_data_dir()
        except Exception:
            _LOGGER.exception(
                "failed to create user-friendly data directory, which is really strange, but it's not fatal"
            )

    agent_state = ktp_controller.agent.state.load_agent_state()
    if agent_state.finished_at is not None:
        seconds_since_last_finished = max(
            0, (utcnow - agent_state.finished_at).total_seconds()
        )
        if seconds_since_last_finished < 3:
            _LOGGER.warning("Respawning too fast, slow down a bit.")
            time.sleep(3 - seconds_since_last_finished)
    agent = Agent(state=agent_state, is_testbed_mode=args.testbed_mode)
    try:
        agent.run()
    finally:
        final_agent_state = agent.get_state()
        final_agent_state.finished_at = ktp_controller.utils.utcnow()
        ktp_controller.agent.state.save_agent_state(final_agent_state)

    return 0


def run() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--testbed-mode", action="store_true", default=False)

    args = parser.parse_args()

    _LOGGER.info("KTP Controller Agent v%s", VERSION)
    try:
        with ktp_controller.utils.singleton():
            return _run(args)
    finally:
        _LOGGER.info("Bye.")
