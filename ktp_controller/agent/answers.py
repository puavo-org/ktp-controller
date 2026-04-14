# Standard library imports
import logging
import os.path
import pathlib
import time
import zipfile

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.utils

_LOGGER = logging.getLogger(__file__)


__all__ = [
    "write_archive_file",
    "mark_dir_archived",
    "mark_file_archived",
    "transfer_answers",
    "create_dummy_exam_package_file",
]


def write_archive_file(archive_filepath: str) -> None:
    """Write a timestamped sentinel file to mark something as archived.

    Raises FileExistsError if the sentinel file already exists.
    """
    utcnow_str = ktp_controller.utils.utcnow_str()

    if os.path.exists(archive_filepath):
        raise FileExistsError(archive_filepath)

    with ktp_controller.utils.open_atomic_write(
        archive_filepath, exclusive=True, encoding="utf-8"
    ) as sentinel_file:
        sentinel_file.write(utcnow_str)
        sentinel_file.write("\n")


def mark_dir_archived(dirpath: str | pathlib.Path) -> None:
    """Write a .archived sentinel file inside dirpath."""
    write_archive_file(os.path.join(dirpath, ".archived"))


def mark_file_archived(filepath: str | pathlib.Path) -> None:
    """Write a <filepath>.archived sentinel file alongside filepath."""
    write_archive_file(f"{filepath}.archived")


async def transfer_answers(
    *,
    exam_package_external_id: str | None,
    is_final: ktp_controller.examomatic.client.IsFinal,
) -> None:
    """Download answers from Abitti2 and upload them to Exam-O-Matic.

    If exam_package_external_id is None the answers are saved locally as
    orphan files (they cannot be uploaded because Exam-O-Matic requires a
    known exam package).
    """
    start_time_monotonic = time.monotonic()

    suffix = ktp_controller.utils.utcnow_str() + ("_final" if is_final else "")

    if exam_package_external_id is None:
        answers_file_path = ktp_controller.files.get_local_filepath(
            ktp_controller.files.LocalFilepathType.ORPHAN_ANSWERS_FILE,
            "unknown",
            suffix,
        )
    else:
        answers_file_path = ktp_controller.files.get_local_filepath(
            ktp_controller.files.LocalFilepathType.ANSWERS_FILE,
            exam_package_external_id,
            suffix,
        )

    try:
        deleted_answers_files = ktp_controller.files.cleanup_old_answers_files()
    except Exception:
        # cleanup_old_answers_files is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        _LOGGER.exception("Failed to cleanup some old answers files")
    else:
        _LOGGER.info("Deleted %d old answers files", len(deleted_answers_files))

    deleted_exam_package_external_ids: set = set()
    try:
        ktp_controller.files.cleanup_archived_exam_packages(
            deleted_exam_package_external_ids=deleted_exam_package_external_ids
        )
    except Exception:
        # cleanup_archived_exam_packages is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        _LOGGER.exception("Failed to cleanup some old exam packages")

    _LOGGER.info("Deleted %d old exam packages", len(deleted_exam_package_external_ids))

    sha256sum = await ktp_controller.abitti2.client.download_answers_file(
        answers_file_path,
        timeout=(6.1, 200),
    )

    if exam_package_external_id is None:
        _LOGGER.warning("Orphan answers file cannot be uploaded: %r", answers_file_path)
        return

    await ktp_controller.examomatic.client.upload_answers_file(
        exam_package_external_id=exam_package_external_id,
        filepath=answers_file_path,
        sha256sum=sha256sum,
        is_final=is_final,
        timeout=(60.1, 600),
    )

    try:
        mark_file_archived(answers_file_path)
    except Exception as exception:
        _LOGGER.warning(
            "Failed to mark answers file %r archived: %s", answers_file_path, exception
        )

    exam_package_dirpath = ktp_controller.files.get_local_dirpath(
        ktp_controller.files.LocalFilepathType.EXAM_PACKAGE, exam_package_external_id
    )

    try:
        mark_dir_archived(exam_package_dirpath)
    except Exception as exception:
        _LOGGER.warning(
            "Failed to mark exam package dir %r archived: %s",
            exam_package_dirpath,
            exception,
        )

    duration = time.monotonic() - start_time_monotonic

    _LOGGER.info(
        "Transferred answers file '%s' from Abitti2 to Exam-O-Matic in %.1f seconds.",
        os.path.basename(answers_file_path),
        duration,
    )


def create_dummy_exam_package_file() -> None:
    """Create the dummy exam package file that Abitti2 uses for reset."""
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
