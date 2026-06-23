# Standard library imports
import hashlib
import logging
import os.path
import typing
import zipfile

# Internal imports
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "ExamPackageError",
    "ExamPackageUsageError",
    "create_dummy_exam_package_file",
    "create_exam_package_file",
    "set_current_exam_package_state",
]


class ExamPackageError(Exception):
    pass


class ExamPackageUsageError(ExamPackageError):
    def __init__(self, error_message: str):
        super().__init__(self)
        self._error_message = error_message

    def __str__(self) -> str:
        return f"usage error: {self._error_message}"


def create_dummy_exam_package_file() -> None:
    """Create the dummy exam package file that Abitti2 uses for reset."""
    ktp_controller.examomatic.client.download_dummy_exam_file(
        ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH
    )

    with (
        ktp_controller.utils.open_atomic_write(
            ktp_controller.files.DUMMY_EXAM_PACKAGE_FILEPATH
        ) as exam_package_file,
        zipfile.ZipFile(exam_package_file, "w") as exam_package_file_zip,
    ):
        exam_package_file_zip.write(
            ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH,
            os.path.basename(ktp_controller.files.DUMMY_EXAM_FILE_FILEPATH),
        )


async def create_exam_package_file(
    api_scheduled_exam_package,
) -> tuple[str, set[str]]:
    """Download individual exam files and bundle them into a single zip package.

    Returns a tuple of (exam_package_filepath, decrypt_codes).
    """

    _LOGGER.info(
        "creating exam package file for scheduled exam package %r...",
        api_scheduled_exam_package["external_id"],
    )

    exam_file_infos = {}
    for api_scheduled_exam_external_id in api_scheduled_exam_package[
        "scheduled_exam_external_ids"
    ]:
        api_scheduled_exam = await ktp_controller.api.client.get_scheduled_exam(
            api_scheduled_exam_external_id
        )
        exam_file_info = api_scheduled_exam["exam_file_info"]
        exam_file_sha256 = exam_file_info["sha256"].lower()
        if exam_file_sha256 in exam_file_infos:
            _LOGGER.warning(
                "Duplicate exam file detected! Exam file with SHA256 %r is already in the package, skipping %r",
                exam_file_sha256,
                exam_file_info,
            )
            continue
        exam_file_infos[exam_file_sha256] = exam_file_info

    decrypt_codes: set[str] = set()
    exam_package_filepath = ktp_controller.files.get_local_filepath(
        ktp_controller.files.LocalFilepathType.EXAM_PACKAGE,
        api_scheduled_exam_package["external_id"],
        hashlib.sha256("".join(sorted(exam_file_infos)).encode("ascii")).hexdigest(),
    )

    with (
        ktp_controller.utils.open_atomic_write(
            exam_package_filepath
        ) as exam_package_file,
        zipfile.ZipFile(exam_package_file, "w") as exam_package_file_zip,
    ):
        for exam_file_info in exam_file_infos.values():
            exam_package_file_zip.write(
                ktp_controller.files.get_local_filepath(
                    ktp_controller.files.LocalFilepathType.EXAM_FILE,
                    exam_file_info["external_id"],
                    exam_file_info["sha256"],
                ),
                ktp_controller.utils.utcnow_str() + exam_file_info["name"],
            )
            decrypt_codes.add(exam_file_info["decrypt_code"])

    _LOGGER.info(
        "created exam package file %r with %d exams",
        exam_package_filepath,
        len(exam_file_infos),
    )

    return exam_package_filepath, decrypt_codes


async def set_current_exam_package_state(
    current_exam_package: dict[str, typing.Any], next_state: str
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
