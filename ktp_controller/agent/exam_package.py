# Standard library imports
import enum
import hashlib
import logging
import typing
import zipfile

# Internal imports
import ktp_controller.api.client
import ktp_controller.files
import ktp_controller.utils

_LOGGER = logging.getLogger(__file__)


__all__ = [
    "Trigger",
    "Component",
    "ExamPackageError",
    "ExamPackageUsageError",
    "create_exam_package_file",
    "set_current_exam_package_state",
]


class Trigger(str, enum.Enum):
    """Reason why the exam package state machine was evaluated."""

    TIME = "time"
    MANUAL_PREPARE = "manual_prepare"
    MANUAL_START = "manual_start"
    MANUAL_STOP = "manual_stop"
    MANUAL_ARCHIVE = "manual_archive"

    def __str__(self) -> str:
        return self.value


class Component(str, enum.Enum):
    """External component the agent maintains a WebSocket connection to."""

    API = "API"
    EXAMOMATIC = "Exam-O-Matic"
    ABITTI2 = "Abitti2"

    def __str__(self) -> str:
        return self.value


class ExamPackageError(Exception):
    pass


class ExamPackageUsageError(ExamPackageError):
    def __init__(self, error_message: str):
        super().__init__(self)
        self._error_message = error_message

    def __str__(self) -> str:
        return f"usage error: {self._error_message}"


async def create_exam_package_file(
    api_scheduled_exam_package,
) -> typing.Tuple[str, typing.Set[str]]:
    """Download individual exam files and bundle them into a single zip package.

    Returns a tuple of (exam_package_filepath, decrypt_codes).
    """
    exam_file_infos = []
    for api_scheduled_exam_external_id in api_scheduled_exam_package[
        "scheduled_exam_external_ids"
    ]:
        api_scheduled_exam = await ktp_controller.api.client.get_scheduled_exam(
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


async def set_current_exam_package_state(
    current_exam_package: typing.Dict[str, typing.Any], next_state: str
) -> bool:
    """Transition the exam package to next_state via the API.

    Mutates current_exam_package["state"] in-place and returns True when the
    state actually changed (i.e. it was not already next_state).
    """
    last_state = await ktp_controller.api.client.set_current_exam_package_state(
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
