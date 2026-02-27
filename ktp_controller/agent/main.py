# Standard library imports
import asyncio
import contextlib
import datetime
import enum
import hashlib
import json
import logging
import os.path
import time
import typing
import zipfile

# Third-party imports
import pydantic
import requests.exceptions
import websockets

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.abitti2.naksu2
import ktp_controller.abitti2.schemas
import ktp_controller.abitti2.utils
import ktp_controller.agent.state
import ktp_controller.agent.stats
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.pydantic
import ktp_controller.utils
import ktp_controller.messages
import ktp_controller.schemas

from ktp_controller.settings import SETTINGS

_LOGGER = logging.getLogger(__file__)


def _validate_security_code(security_code: typing.Dict[str, str]) -> None:
    if not isinstance(security_code, dict):
        raise ValueError("not dict")
    if set(security_code.keys()) != {"keyCode", "confirmationCode"}:
        raise ValueError("has invalid keys")
    if not isinstance(security_code["keyCode"], str):
        raise ValueError("keyCode is not str")
    if not isinstance(security_code["confirmationCode"], str):
        raise ValueError("confirmationCode is not str")


def _security_code_to_student_access_code(
    security_code: typing.Dict[str, str] | None,
) -> ktp_controller.schemas.StudentAccessCode | None:
    if security_code is None:
        return None

    return ktp_controller.schemas.StudentAccessCode(
        key_code=security_code["keyCode"],
        verification_code=security_code["confirmationCode"],
    )


def _create_dummy_exam_package_file():
    ktp_controller.examomatic.client.download_dummy_exam_file(
        ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH
    )

    with ktp_controller.utils.open_atomic_write(
        ktp_controller.files.DUMMY_EXAM_PACKAGE_FILEPATH
    ) as exam_package_file:
        with zipfile.ZipFile(exam_package_file, "w") as exam_package_file_zip:
            exam_package_file_zip.write(
                ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH,
                os.path.basename(ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH),
            )


def _transfer_answers(
    exam_package_external_id: str,
    *,
    is_final: ktp_controller.examomatic.client.IsFinal = ktp_controller.examomatic.client.IsFinal.UNKNOWN,
):
    start_time_monotonic = time.monotonic()

    answers_file_path = ktp_controller.files.get_local_filepath(
        ktp_controller.files.LocalFilepathType.ANSWERS_FILE,
        exam_package_external_id,
        ktp_controller.utils.utcnow_str() + ("_final" if is_final else ""),
    )

    sha256sum = ktp_controller.abitti2.client.download_answers_file(answers_file_path)

    ktp_controller.examomatic.client.upload_answers_file(
        exam_package_external_id=exam_package_external_id,
        filepath=answers_file_path,
        sha256sum=sha256sum,
        is_final=is_final,
    )

    duration = time.monotonic() - start_time_monotonic

    _LOGGER.info(
        "Transferred answer file '%s' from Abitti2 to Exam-O-Matic' in %.1f seconds.",
        os.path.basename(answers_file_path),
        duration,
    )


def _create_exam_package_file(
    api_scheduled_exam_package,
) -> typing.Tuple[str, typing.Set[str]]:
    exam_file_infos = []
    for api_scheduled_exam_external_id in api_scheduled_exam_package[
        "scheduled_exam_external_ids"
    ]:
        api_scheduled_exam = ktp_controller.api.client.get_scheduled_exam(
            api_scheduled_exam_external_id
        )
        exam_file_infos.append(api_scheduled_exam["exam_file_info"])

    decrypt_codes: typing.Set[str] = set()
    exam_package_filepath = ktp_controller.files.get_local_filepath(
        ktp_controller.files.LocalFilepathType.EXAM_PACKAGE,
        api_scheduled_exam_package["external_id"],
        hashlib.sha256(
            "".join(sorted([i["sha256"] for i in exam_file_infos])).encode("ascii")
        ).hexdigest(),
    )

    with ktp_controller.utils.open_atomic_write(
        exam_package_filepath
    ) as exam_package_file:
        with zipfile.ZipFile(exam_package_file, "w") as exam_package_file_zip:
            for exam_file_info in exam_file_infos:
                exam_package_file_zip.write(
                    ktp_controller.files.get_local_filepath(
                        ktp_controller.files.LocalFilepathType.EXAM_FILE,
                        exam_file_info["external_id"],
                        exam_file_info["sha256"],
                    ),
                    ktp_controller.utils.utcnow_str() + exam_file_info["name"],
                )
                decrypt_codes.add(exam_file_info["decrypt_code"])

    return exam_package_filepath, decrypt_codes


def _set_current_exam_package_state(
    current_exam_package: typing.Dict[str, typing.Any], next_state: str
) -> bool:
    last_state = ktp_controller.api.client.set_current_exam_package_state(
        current_exam_package["external_id"], next_state
    )

    current_exam_package["state"] = next_state

    _LOGGER.debug(
        "Changed state from %s to %s of the current exam package: %s",
        last_state,
        next_state,
        current_exam_package,
    )

    return last_state != next_state


def _allow_students_to_use_browsers(students):
    for student in students:
        student_uuid = student["studentUuid"]
        session_uuid = student["sessionUuid"]
        student_status = student["studentStatus"]

        if student_status != "waiting-for-auth-browser":
            continue

        try:
            ktp_controller.abitti2.client.set_exam_session_permission_to_use_browsers(
                session_uuid, True
            )
        except Exception:
            _LOGGER.error(
                "failed to allow student %s to use browsers in session %s",
                student_uuid,
                session_uuid,
            )
            continue

        _LOGGER.info(
            "allowed student %s to use browsers in session %s",
            student_uuid,
            session_uuid,
        )


def _all_students_have_left_or_finished(
    status_report: typing.Dict[str, typing.Any],
) -> bool:
    """
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": []}}})
    True
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": [{"age": 13}]}}})
    False
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": [{"examFinished": True}]}}})
    True
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": [{"examFinished": True}, {"examFinished": False}]}}})
    False
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": [{"examFinished": True}, {"sessionStatus": "session_started"}]}}})
    False
    >>> _all_students_have_left_or_finished({"status": {"data": {"students": [{"examFinished": True}, {"sessionStatus": "session_ended"}]}}})
    True
    """

    return all(
        s.get("examFinished", False)
        or s.get("sessionStatus") in ("session_ended", "exam_finished_by_student")
        for s in status_report["status"]["data"]["students"]
    )


class Trigger(str, enum.Enum):
    TIME = "time"
    MANUAL_PREPARE = "manual_prepare"
    MANUAL_START = "manual_start"
    MANUAL_STOP = "manual_stop"
    MANUAL_ARCHIVE = "manual_archive"

    def __str__(self) -> str:
        return self.value


class Component(str, enum.Enum):
    API = "API"
    EXAMOMATIC = "Exam-O-Matic"
    ABITTI2 = "Abitti2"

    def __str__(self) -> str:
        return self.value


class _Error(Exception):
    pass


class _UsageError(_Error):
    def __init__(self, error_message: str):
        super().__init__(self)
        self.__error_message: str = error_message

    def __str__(self) -> str:
        return f"usage error: {self.__error_message}"


class Agent:
    def __init__(
        self,
        *,
        approx_api_ping_interval_sec: int = 15,
        approx_api_status_report_interval_sec: int = 30,
        approx_examomatic_ping_interval_sec: int = SETTINGS.examomatic_ping_interval_sec,
        approx_restart_timeout_sec: int = 5,
        approx_answer_transfer_interval_sec: int = SETTINGS.answer_transfer_interval_sec,
        state: ktp_controller.agent.state.AgentState,
    ):
        self.__state = state
        self.__answer_transfer_task = None

        self.__approx_api_ping_interval_sec = approx_api_ping_interval_sec
        self.__approx_api_status_report_interval_sec = (
            approx_api_status_report_interval_sec
        )
        self.__approx_examomatic_ping_interval_sec = approx_examomatic_ping_interval_sec
        self.__approx_restart_timeout_sec = approx_restart_timeout_sec
        self.__approx_answer_transfer_interval_sec = approx_answer_transfer_interval_sec

        # Abitti2 reports these
        self.__last_received_exam_list = None
        self.__last_received_security_code = None
        self.__old_security_code = None

        self.__connection_stats: typing.Dict[
            Component, ktp_controller.agent.stats.ConnectionStats
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
        }

    @property
    def __is_auto_control_enabled(self) -> bool:
        return self.__state.is_auto_control_enabled

    @__is_auto_control_enabled.setter
    def __is_auto_control_enabled(self, value: bool) -> None:
        self.__state.is_auto_control_enabled = value

    def __set_auto_control(
        self,
        command_uuid: str,
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

    async def __command_enable_auto_control(
        self,
        command_uuid: str,
        command_data: ktp_controller.messages.CommandData,
    ) -> ktp_controller.messages.CommandResultData:
        return self.__set_auto_control(command_uuid, True)

    async def __command_disable_auto_control(
        self,
        command_uuid: str,
        command_data: ktp_controller.messages.CommandData,
    ):
        return self.__set_auto_control(command_uuid, False)

    async def __command_change_current_exam_package_state(
        self,
        command_uuid: str,
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
        current_exam_package: typing.Dict[str, typing.Any],
    ) -> bool:
        _LOGGER.info("Preparing exam package: %r", current_exam_package)

        (exam_package_filepath, decrypt_codes) = _create_exam_package_file(
            current_exam_package
        )

        exam_filenames = ktp_controller.abitti2.client.prepare_exam_package(
            exam_package_filepath, decrypt_codes
        )
        _LOGGER.info(
            "Prepared current exam package %r (%d exams) successfully.",
            current_exam_package["external_id"],
            len(exam_filenames),
        )

        return True

    def __ensure_answer_transfer_task_is_running(
        self, current_exam_package: typing.Dict[str, typing.Any]
    ):
        if self.__answer_transfer_task is None:
            self.__answer_transfer_task = asyncio.create_task(
                self.__transfer_non_final_answers_periodically(current_exam_package)
            )
            _LOGGER.info(
                "Started to transfer exam package '%s' answer files from Abitti2 to Exam-O-Matic periodically (approx. once per %d seconds).",
                current_exam_package["external_id"],
                self.__approx_answer_transfer_interval_sec,
            )

    async def __stop_answer_transfer_task(
        self, current_exam_package: typing.Dict[str, typing.Any]
    ):
        if self.__answer_transfer_task is None:
            _LOGGER.error("Cannot stop answer transfer task, because it's not running!")
            return

        self.__answer_transfer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.__answer_transfer_task
        _LOGGER.info(
            "Stopped periodic exam package '%s' answer file transfers from Abitti2 to Exam-O-Matic.",
            current_exam_package["external_id"],
        )
        self.__answer_transfer_task = None

    async def __start_current_exam_package(
        self,
        current_exam_package: typing.Dict[str, typing.Any],
    ) -> bool:
        _LOGGER.info("Starting exam package: %r", current_exam_package)

        if self.__is_auto_control_enabled:
            if self.__old_security_code is None:
                self.__old_security_code = self.__last_received_security_code
                _LOGGER.info(
                    "Requesting Abitti2 to change the access code to ensure students "
                    "cannot access new exams with the old code (%r).",
                    self.__old_security_code,
                )
                ktp_controller.abitti2.client.change_student_access_code()
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
                ktp_controller.api.client.get_student_access_code(),
            )

        self.__old_security_code = None
        ktp_controller.abitti2.client.start_decrypted_exams()
        _LOGGER.info(
            "Started current exam package %r successfully.",
            current_exam_package["external_id"],
        )

        return True

    async def __start_stopping_current_exam_package(
        self, current_exam_package: typing.Dict[str, typing.Any]
    ) -> bool:
        await self.__stop_current_exam_package(current_exam_package)
        return True  # Always proceed to the next state, we have started to stop the current exam.

    async def __stop_current_exam_package(
        self,
        current_exam_package: typing.Dict[str, typing.Any],
    ) -> bool:
        if self.__is_auto_control_enabled:
            # Change the security code first to ensure students cannot enter anymore.
            ktp_controller.abitti2.client.change_student_access_code()

        status_report = ktp_controller.api.client.get_last_status_report()
        if status_report is None:
            return False
        for student in status_report["status"]["data"]["students"]:
            ktp_controller.abitti2.client.stop_exam_session(student["sessionUuid"])

        is_stopped = (
            _all_students_have_left_or_finished(status_report)
            and current_exam_package["state"] == "stopping"
            and status_report["received_at"] > current_exam_package["state_changed_at"]
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
        current_exam_package: typing.Dict[str, typing.Any],
    ) -> bool:
        await self.__stop_answer_transfer_task(current_exam_package)
        self.__transfer_answers(
            current_exam_package, is_final=ktp_controller.examomatic.client.IsFinal.TRUE
        )
        ktp_controller.abitti2.client.reset()
        return True

    def __transfer_answers(
        self,
        current_exam_package: typing.Dict[str, typing.Any],
        is_final: ktp_controller.examomatic.client.IsFinal,
    ) -> None:
        is_final = ktp_controller.examomatic.client.IsFinal(is_final)
        status_report = ktp_controller.api.client.get_last_status_report()
        if (
            status_report is None
            or status_report["status"]["data"]["answerPaperCount"] is None
        ):
            _LOGGER.warning(
                "I don't know yet if there are answers to transfer, "
                "but I won't take the risk of trying to download them from Abitti2, "
                "because Abitti2 can block indefinitely if there are no answers."
            )
            return
        if status_report["status"]["data"]["answerPaperCount"] > 0:
            _transfer_answers(
                current_exam_package["external_id"],
                is_final=is_final,
            )
        else:
            # If there are no answers, Abitti2 blocks download
            # requests indefinitely.
            _LOGGER.warning("There are no answers to transfer.")

    async def __transfer_non_final_answers_periodically(
        self, current_exam_package: typing.Dict[str, typing.Any]
    ):
        while True:
            self.__transfer_answers(
                current_exam_package,
                is_final=ktp_controller.examomatic.client.IsFinal.UNKNOWN,
            )
            await asyncio.sleep(self.__approx_answer_transfer_interval_sec)

    async def __work_on_current_exam_package(self, *, trigger: Trigger) -> bool:
        utcnow = ktp_controller.utils.utcnow()
        trigger = Trigger(trigger)  # Raises ValueError if trigger is not a Trigger.

        if trigger.startswith("manual_") and self.__is_auto_control_enabled:
            raise RuntimeError(
                "Critical internal logic error!. "
                "Auto control is enabled and manual trigger encountered. "
                "This is an usage error which should have been properly handled "
                "and reported by upper levels in the call stack."
            )

        locked_exam_packages = ktp_controller.api.client.get_locked_exam_packages()

        if len(locked_exam_packages) == 0:
            if self.__is_auto_control_enabled and self.__last_received_exam_list == []:
                _LOGGER.info("Reseting Abitti2 with a dummy exam package...")
                ktp_controller.abitti2.client.reset()
                _LOGGER.info("Abitti2 was reset.")
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

        status_report = ktp_controller.api.client.get_last_status_report()
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

        state_transitions = {
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
                        _all_students_have_left_or_finished(status_report)
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
        if state in ("running", "stopping", "stopped"):
            self.__ensure_answer_transfer_task_is_running(current_exam_package)

        transition = state_transitions[state]

        if trigger not in transition["valid_triggers"]:
            raise _UsageError(
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
                changed = _set_current_exam_package_state(
                    current_exam_package, transition["next_state"]
                )

        if changed:
            _LOGGER.debug(
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

    async def __send_pings_to_api(self, websock):
        while True:
            message = ktp_controller.messages.PingMessage().model_dump_json()
            await websock.send(message)
            _LOGGER.debug("--> API: %s", message)
            await asyncio.sleep(self.__approx_api_ping_interval_sec)

    async def __send_status_reports_to_api(self, websock):
        while True:
            message = ktp_controller.messages.StatusReportMessage(
                data=ktp_controller.messages.StatusReportData(
                    is_auto_control_enabled=self.__is_auto_control_enabled
                ),
            ).model_dump_json()
            await websock.send(message)
            _LOGGER.debug("--> API: %s", message)
            await asyncio.sleep(self.__approx_api_status_report_interval_sec)

    async def __send_pings_to_examomatic(self, websock):
        while True:
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

    async def __communicate_with_api(self, websock):
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
                    command_data = ktp_controller.messages.CommandData.model_validate(
                        message["data"]
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
                        command_result = await self.__commands[command_data.command](
                            message["uuid"], command_data
                        )
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
                            "Executed command %r successfully.", command_data.command
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

    async def __communicate_with_examomatic(self, websock):
        async for data in websock:
            received_at = ktp_controller.utils.utcnow()
            _LOGGER.debug("<-- Exam-O-Matic: %s", data)
            try:
                message = ktp_controller.examomatic.client.websock_validate_message(
                    data
                )
            except ValueError:
                _LOGGER.exception("received invalid data from Exam-O-Matic: %r", data)
                continue

            self.__connection_stats[
                Component.EXAMOMATIC
            ].last_message_received_at = received_at

            if message["type"] == "pong":
                self.__connection_stats[Component.EXAMOMATIC].ping_pong_count += 1
                if (
                    self.__connection_stats[Component.EXAMOMATIC].refresh_exams_count
                    == 0
                ):
                    try:
                        self.__refresh_exams(is_spontaneous=True)
                    except Exception:
                        _LOGGER.exception("Failed to refresh exams")
                continue  # pongs are not acked

            if message["type"] == "change_keycode":
                _LOGGER.info("received change_keycode message from Exam-O-Matic")
                if not self.__is_auto_control_enabled:
                    _LOGGER.error(
                        "Keycode cannot be changed by Exam-O-Matic, because auto control is not enabled."
                    )
                    continue
                try:
                    ktp_controller.abitti2.client.change_student_access_code()
                except Exception:
                    _LOGGER.exception("Failed to changed student access code")
                    continue  # Failed requests are not acked
                _LOGGER.info("Keycode changed.")
            elif message["type"] == "refresh_exams":
                _LOGGER.info("received refresh_exams message from Exam-O-Matic")
                try:
                    self.__refresh_exams(is_spontaneous=False)
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
        message: None,
    ):
        await websock.send("pong")

    async def __handle_abitti2_security_code_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: typing.Dict[str, typing.Any],
    ):
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
            _validate_security_code(security_code)
        except ValueError as value_error:
            _LOGGER.error(
                "received invalid security code from Abitti2: %s: %r",
                value_error,
                security_code,
            )
            return

        self.__last_received_security_code = security_code

        status_report = ktp_controller.api.client.get_last_status_report()
        if status_report is None:
            return

        self.__send_status_report(received_at, status_report["status"])

    def __validate_abitti2_stats_message(
        self, message: typing.Dict[str, typing.Any]
    ) -> bool:
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
        message: typing.Dict[str, typing.Any],
    ):
        ktp_controller.abitti2.utils.sanitize_stats_message(message)

        if (
            self.__validate_abitti2_stats_message(message)
            and self.__is_auto_control_enabled
        ):
            _allow_students_to_use_browsers(message["data"]["students"])

        self.__send_status_report(received_at, message)

    def __send_status_report(
        self,
        received_at: datetime.datetime,
        message: typing.Dict[str, typing.Any],
    ):
        # TODO: remove when Exam-O-Matic reads this via abitti2.student_access_code
        message["singleSecurityCode"] = self.__last_received_security_code

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
            abitti2_version = (
                ktp_controller.abitti2.client.get_current_abitti2_version()
            )
        except Exception:
            _LOGGER.exception("failed to get current Abitti2 version")
            abitti2_version = None

        status_report = {
            "monitoring_passphrase": supervisor_passphrase,
            "server_version": abitti2_version,
            "status": message,
            "received_at": ktp_controller.utils.strfdt(received_at),
            "exams": self.__last_received_exam_list,
            "abitti2": {
                "domain": domain,
                "student_access_code": _security_code_to_student_access_code(
                    self.__last_received_security_code
                ),
            },
        }

        try:
            ktp_controller.examomatic.client.send_status_report(status_report)
            status_report["reported_at"] = ktp_controller.utils.utcnow_str()
            _LOGGER.debug("sent status report to Exam-O-Matic")
        except Exception:
            _LOGGER.exception("failed to send status report to Exam-O-Matic")
            status_report["reported_at"] = None

        ktp_controller.api.client.send_status_report(status_report)
        _LOGGER.debug("sent status report to KTP Controller API")

    async def __handle_abitti2_exams_message(
        self,
        websock: websockets.ClientConnection,
        received_at: datetime.datetime,
        message: typing.Dict[str, typing.Any],
    ):
        self.__last_received_exam_list = message["data"]

    def __decode_abitti2_message(
        self, data
    ) -> typing.Tuple[str | None, typing.Dict[str, typing.Any] | None]:
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

    async def __communicate_with_abitti2(self, websock):
        async for data in websock:
            received_at = ktp_controller.utils.utcnow()

            _LOGGER.debug("<-- Abitti2: %s", data)

            message_type, message = self.__decode_abitti2_message(data)
            if message_type is None:
                continue

            try:
                handler = {
                    "ping": self.__handle_abitti2_ping_message,
                    "security-code": self.__handle_abitti2_security_code_message,
                    "stats": self.__handle_abitti2_stats_message,
                    "exams": self.__handle_abitti2_exams_message,
                    "servers": None,  # Simply ignored for now
                }[message_type]
            except KeyError:
                _LOGGER.warning("unhandled %r message from Abitti2", message_type)
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
        name: str,
        url: str,
        asyncfuncs: typing.Awaitable,
        *,
        connection_stats_class: type[ktp_controller.agent.stats.ConnectionStats],
        additional_headers: typing.Dict[str, str] | None = None,
    ):
        while True:
            try:
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
            except ExceptionGroup as eg:
                _LOGGER.error(
                    "Websocket connection to %s has failed!",
                    name,
                    exc_info=eg.exceptions[0],
                )
                _LOGGER.error(
                    "Reconnect to %s in approximately %d seconds...",
                    name,
                    self.__approx_restart_timeout_sec,
                )
                await asyncio.sleep(self.__approx_restart_timeout_sec)
            finally:
                self.__connection_stats.pop(name, None)

    async def __maintain_websocket_connection_to_api(self):
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

    async def __maintain_websocket_connection_to_examomatic(self):
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

    async def __maintain_websocket_connection_to_abitti2(self):
        await self.__maintain_websocket_connection(
            Component.ABITTI2,
            ktp_controller.abitti2.client.get_abitti2_websock_url(),
            [
                self.__communicate_with_abitti2,
            ],
            connection_stats_class=ktp_controller.agent.stats.Abitti2ConnectionStats,
            additional_headers=ktp_controller.abitti2.client.get_basic_auth(),
        )

    def __ensure_exam_file_exists(self, eom_scheduled_exam):
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
            ktp_controller.examomatic.client.download_exam_file(
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

    def __refresh_exams(self, *, is_spontaneous: bool):
        _LOGGER.info(
            "Starting %sexam refresh...", "spontaneous " if is_spontaneous else ""
        )

        try:
            eom_exam_info = ktp_controller.examomatic.client.get_exam_info()
        except requests.exceptions.HTTPError as http_error:
            if http_error.response.status_code == 404:
                if is_spontaneous:
                    # It's ok that there are no exam infos, because we
                    # are doing spontaneous refresh and we had no
                    # prior knowledge about availability exam infos.
                    _LOGGER.info("No exam info available.")
                else:
                    _LOGGER.error(
                        "No exam info available, but we have been told that there should be!"
                    )
            else:
                _LOGGER.exception("Failed to refresh exams")
            return

        _LOGGER.debug("Received exam info from Exam-O-Matic: %s:", eom_exam_info)

        for eom_scheduled_exam in eom_exam_info["schedules"]:
            self.__ensure_exam_file_exists(eom_scheduled_exam)

        ktp_controller.api.client.save_exam_info(eom_exam_info)

        _LOGGER.info("refreshed exams successfully")

    async def forever(self):
        while True:
            _LOGGER.info("Start!")

            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.__maintain_websocket_connection_to_api())
                    tg.create_task(self.__maintain_websocket_connection_to_abitti2())
                    tg.create_task(self.__maintain_websocket_connection_to_examomatic())
            except* Exception:
                _LOGGER.exception("Operational failure")
                _LOGGER.error(
                    "Restart approximately in %d seconds...",
                    self.__approx_restart_timeout_sec,
                )
                await asyncio.sleep(self.__approx_restart_timeout_sec)

    def run(self):
        # ktp_controller.abitti2.client needs dummy exam package to reset Abitti2.
        _create_dummy_exam_package_file()

        asyncio.run(self.forever())

    def get_state(self) -> ktp_controller.agent.state.AgentState:
        return self.__state.model_copy()


def _run() -> int:
    agent_state = ktp_controller.agent.state.load_agent_state()
    agent = Agent(state=agent_state)
    try:
        agent.run()
    finally:
        ktp_controller.agent.state.save_agent_state(agent.get_state())

    return 0


def run() -> int:
    with ktp_controller.utils.singleton():
        return _run()
