# Standard library imports
import hashlib
import logging
import os
import os.path
import re
import typing

# Third-party imports
import httpx

import ktp_controller.abitti2.naksu2

# Internal imports
import ktp_controller.files
import ktp_controller.httpx
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    # Utils:
    "get_basic_auth",
    "get_abitti2_websock_url",
    # Abitti2 API commands:
    "get_current_abitti2_version",
    "change_student_access_code",
    "decrypt_exams",
    "upload_exam_package",
    "get_decrypted_exams",
    "start_decrypted_exams",
    "reset",
    "stop_exam_session",
    "download_answers_file",
]


# Constants:


ABITTI2_SUPERVISOR_USERNAME = "valvoja"


async def _get(path: str, **kwargs) -> httpx.Response:
    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    kwargs["auth"] = (
        ABITTI2_SUPERVISOR_USERNAME,
        ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
    )

    return await ktp_controller.httpx.get(url, **kwargs)


async def _post(path: str, **kwargs) -> httpx.Response:
    kwargs.setdefault("json", {})

    kwargs["auth"] = (
        ABITTI2_SUPERVISOR_USERNAME,
        ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
    )

    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    return await ktp_controller.httpx.post(url, **kwargs)


def get_basic_auth() -> dict[str, str]:
    return ktp_controller.utils.get_basic_auth(
        ABITTI2_SUPERVISOR_USERNAME,
        ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
    )


def get_abitti2_websock_url():
    return ktp_controller.utils.get_url(
        ktp_controller.abitti2.naksu2.read_domain(),
        "/ws/data",
        scheme="wss",
    )


# Abitti2 API commands:


async def get_current_abitti2_version() -> str:
    try:
        # Abitti2 1.26.0+
        response = await _get("/api/server-info")
        version = response.json()["version"]
    except httpx.HTTPStatusError as http_error:
        if http_error.response.status_code != 404:
            raise
        # Pre Abitti2 1.26.0
        response = await _get("/api/version")
        version = response.json()["version"]

    version_match = re.match(r"^SERVER-v((\d+)\.(\d+)\.(\d+))$", version)
    if not version_match:
        raise RuntimeError("Abitti2 reported version in unexpected format", version)
    return version_match.group(1)


async def change_student_access_code() -> dict:
    response = await _post("/api/single-security-code")
    return response.json()


async def decrypt_exams(decrypt_code: str, **kwargs) -> dict:
    response = await _post(
        "/api/decrypt-exam", json={"decryptPassword": decrypt_code}, **kwargs
    )
    return response.json()


async def upload_exam_package(exam_package_filepath, **kwargs) -> list[str]:
    exam_package_filename = os.path.basename(exam_package_filepath)

    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, "/api/load-exam")

    with open(exam_package_filepath, "rb") as exam_package_file:
        kwargs["auth"] = (
            ABITTI2_SUPERVISOR_USERNAME,
            ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
        )
        kwargs["files"] = {
            "examZip": (
                exam_package_filename,
                exam_package_file,
                "application/zip",
            )
        }
        response = await ktp_controller.httpx.post(url, **kwargs)
        return response.json()


async def get_decrypted_exams() -> dict:
    response = await _get("/api/exams")
    return response.json()


async def start_decrypted_exams() -> dict:
    response = await _post("/api/start-exam")
    return response.json()


async def prepare_exam_package(
    exam_package_filepath: str, decrypt_codes: typing.Iterable[str]
) -> set[str]:
    upload_result = await upload_exam_package(exam_package_filepath)
    exam_filenames = set(upload_result)

    decrypted_exam_filenames = set()
    had_invalid_decrypt_code = False

    for decrypt_code in decrypt_codes:
        retval = await decrypt_exams(decrypt_code)
        if retval["wrongPassword"]:
            _LOGGER.error("invalid decrypt code %r", decrypt_code)
            had_invalid_decrypt_code = True
            continue
        decrypted_exam_filenames.update(retval["mebs"])

    still_encrypted_exam_filenames = exam_filenames - decrypted_exam_filenames

    if len(still_encrypted_exam_filenames) > 0:
        raise RuntimeError(
            f"failed to decrypt {len(still_encrypted_exam_filenames)}/{len(exam_filenames)} exams",
            still_encrypted_exam_filenames,
        )

    if had_invalid_decrypt_code:
        _LOGGER.warning(
            "Encountered an invalid decrypt code, but all exams were "
            "decrypted nevertheless. So, something is crooked!"
        )

    return exam_filenames


async def reset() -> None:
    _LOGGER.info("Reseting Abitti2 with a dummy exam package...")
    await prepare_exam_package(
        ktp_controller.files.DUMMY_EXAM_PACKAGE_FILEPATH, ["odotusaulakoe"]
    )
    await start_decrypted_exams()
    _LOGGER.info("Abitti2 was reset.")


async def stop_exam_session(session_uuid: str) -> None:
    await _post("/api/end-student-session", json={"sessionUuid": session_uuid})


async def download_answers_file(dest_filepath: str, **kwargs) -> str:
    sha256sum = hashlib.sha256()
    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, "/api/answers-zip/answers.meb")

    kwargs["auth"] = (
        ABITTI2_SUPERVISOR_USERNAME,
        ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
    )
    kwargs["chunk_size"] = 4096

    with ktp_controller.utils.open_atomic_write(
        dest_filepath,
        exclusive=True,
        do_makedirs=True,
    ) as dest_file:
        try:
            async for chunk in ktp_controller.httpx.stream_read(url, **kwargs):
                dest_file.write(chunk)
                sha256sum.update(chunk)

        except httpx.ConnectTimeout as connect_timeout:
            raise TimeoutError("Connect timed out.") from connect_timeout
        except (httpx.ReadTimeout, httpx.ReadError) as read_error:
            raise TimeoutError("Read timed out.") from read_error

    return sha256sum.hexdigest()


async def set_exam_session_permission_to_use_browsers(
    session_uuid: str, is_allowed_to_use_browsers: bool
):
    await _post(
        "/api/allow-all-browsers",
        json={"allow": is_allowed_to_use_browsers, "sessionUuid": session_uuid},
    )
