# Standard library imports
import logging
import os.path
import pathlib
import time

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.examomatic.client
import ktp_controller.files
import ktp_controller.utils

_LOGGER = logging.getLogger(__file__)


__all__ = [
    "download_answers_file",
    "upload_answers_file",
]


def _write_archive_file(archive_filepath: str) -> None:
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


def _mark_dir_archived(dirpath: str | pathlib.Path) -> None:
    _write_archive_file(os.path.join(dirpath, ".archived"))


def _mark_file_archived(filepath: str | pathlib.Path) -> None:
    _write_archive_file(f"{filepath}.archived")


def _is_file_archived(filepath: str | pathlib.Path) -> bool:
    return os.path.exists(f"{filepath}.archived")


async def download_answers_file(
    *,
    exam_package_external_id: str,
    is_final: ktp_controller.examomatic.client.IsFinal,
) -> (str, str):
    """Download answers from Abitti2."""
    suffix = ktp_controller.utils.utcnow_str() + ("_final" if is_final else "")

    if is_final:
        existing_final_answers_file_paths = sorted(
            ktp_controller.files.glob_local_filepath(
                ktp_controller.files.LocalFilepathType.ANSWERS_FILE,
                exam_package_external_id,
                "*_final",
            )
        )
        if existing_final_answers_file_paths:
            final_answers_file_path = existing_final_answers_file_paths[0]
            _LOGGER.info(
                "Final answers for exam package %r has already been downloaded: %r",
                exam_package_external_id,
                final_answers_file_path,
            )
            if len(existing_final_answers_file_paths) > 1:
                _LOGGER.warning(
                    "Bizarre situation! There are multiple (%d) final answer files for exam package %r. Picking the first one (%r) and ignoring the rest.",
                    len(existing_final_answers_file_paths),
                    exam_package_external_id,
                    final_answers_file_path,
                )
            return final_answers_file_path, ktp_controller.utils.sha256(
                final_answers_file_path
            )

    answers_file_path = ktp_controller.files.get_local_filepath(
        ktp_controller.files.LocalFilepathType.ANSWERS_FILE,
        exam_package_external_id,
        suffix,
    )

    download_start_time_monotonic = time.monotonic()

    sha256sum = await ktp_controller.abitti2.client.download_answers_file(
        answers_file_path,
        timeout=(6.1, 200),
    )

    download_duration = time.monotonic() - download_start_time_monotonic

    _LOGGER.info(
        "Downloaded answers file '%s' from Abitti2 in %.1f seconds.",
        os.path.basename(answers_file_path),
        download_duration,
    )

    return answers_file_path, sha256sum


async def upload_answers_file(answers_file_path: str) -> bool:
    pathobj = pathlib.Path(answers_file_path)
    pathobj.resolve()

    answers_file_path = str(pathobj)
    answers_file_size = pathobj.stat().st_size
    exam_package_external_id = pathobj.parent.name

    if answers_file_size == 0:
        _LOGGER.warning("Empty answers file cannot be uploaded: %r", answers_file_path)
        return False

    if _is_file_archived(answers_file_path):
        return False

    if answers_file_path.endswith("_final.meb"):
        is_final = ktp_controller.examomatic.client.IsFinal.TRUE
    else:
        is_final = ktp_controller.examomatic.client.IsFinal.FALSE

    upload_start_time_monotonic = time.monotonic()

    _LOGGER.info("Uploading answers file %r to Exam-O-Matic...", answers_file_path)

    await ktp_controller.examomatic.client.upload_answers_file(
        exam_package_external_id=exam_package_external_id,
        filepath=answers_file_path,
        is_final=is_final,
        timeout=(60.1, 600),
    )

    upload_duration = time.monotonic() - upload_start_time_monotonic

    _LOGGER.info(
        "Uploaded answers file '%s' to Exam-O-Matic in %.1f seconds.",
        os.path.basename(answers_file_path),
        upload_duration,
    )

    try:
        _mark_file_archived(answers_file_path)
    except Exception as exception:
        _LOGGER.warning(
            "Failed to mark answers file %r archived: %s", answers_file_path, exception
        )

    _LOGGER.info("Archived answers file %r.", os.path.basename(answers_file_path))

    exam_package_dirpath = ktp_controller.files.get_local_dirpath(
        ktp_controller.files.LocalFilepathType.EXAM_PACKAGE, exam_package_external_id
    )

    try:
        _mark_dir_archived(exam_package_dirpath)
    except Exception as exception:
        _LOGGER.warning(
            "Failed to mark exam package dir %r archived: %s",
            exam_package_dirpath,
            exception,
        )

    _LOGGER.info("Archived exam package directory %r.", exam_package_dirpath)

    return True
