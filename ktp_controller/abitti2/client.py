# Standard library imports
import hashlib
import logging
import os
import os.path
import re
import typing

# Third-party imports
import requests
import requests.auth

# Internal imports
import ktp_controller.files
import ktp_controller.utils
import ktp_controller.abitti2.naksu2


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


# Utils:


def _get(path: str, *, stream: bool = False, timeout: int = 20) -> requests.Response:
    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    response = requests.get(
        url,
        auth=requests.auth.HTTPBasicAuth(
            ABITTI2_SUPERVISOR_USERNAME,
            ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
        ),
        timeout=timeout,
        stream=stream,
    )

    response.raise_for_status()

    return response


def _post(path: str, *, data=None, timeout: int = 20) -> requests.Response:
    if data is None:
        data = {}

    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    response = requests.post(
        url,
        auth=requests.auth.HTTPBasicAuth(
            ABITTI2_SUPERVISOR_USERNAME,
            ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
        ),
        timeout=timeout,
        json=data,
    )

    response.raise_for_status()

    return response


def get_basic_auth() -> typing.Dict[str, str]:
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


def get_current_abitti2_version() -> str:
    version = _get("/api/version").json()["version"]
    version_match = re.match(r"^SERVER-v((\d+)\.(\d+)\.(\d+))$", version)
    if not version_match:
        raise RuntimeError("Abitti2 reported version in unexpected format", version)
    return version_match.group(1)


def change_student_access_code() -> typing.Dict:
    return _post("/api/single-security-code").json()


def decrypt_exams(decrypt_code: str, timeout: int = 60) -> typing.Dict:
    return _post(
        "/api/decrypt-exam", data={"decryptPassword": decrypt_code}, timeout=timeout
    ).json()


def upload_exam_package(
    exam_package_filepath, *, timeout: int = 20
) -> typing.List[str]:
    exam_package_filename = os.path.basename(exam_package_filepath)

    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, "/api/load-exam")

    with open(exam_package_filepath, "rb") as exam_package_file:
        response = requests.post(
            url,
            auth=requests.auth.HTTPBasicAuth(
                ABITTI2_SUPERVISOR_USERNAME,
                ktp_controller.abitti2.naksu2.read_supervisor_passphrase(),
            ),
            timeout=timeout,
            files={
                "examZip": (exam_package_filename, exam_package_file, "application/zip")
            },
        )

        response.raise_for_status()

        return response.json()


def get_decrypted_exams() -> typing.Dict:
    return _get("/api/exams").json()


def start_decrypted_exams() -> typing.Dict:
    return _post("/api/start-exam").json()


def prepare_exam_package(
    exam_package_filepath: str, decrypt_codes: typing.Iterable[str]
) -> typing.Set[str]:
    exam_filenames = set(upload_exam_package(exam_package_filepath))

    decrypted_exam_filenames = set()
    had_invalid_decrypt_code = False
    for decrypt_code in decrypt_codes:
        retval = decrypt_exams(decrypt_code)
        if retval["wrongPassword"]:
            # TODO: is it ok to expose the decrypt code in log files?
            _LOGGER.error(
                "invalid decrypt code (sha1 hash: %r)",
                hashlib.sha1(decrypt_code.encode("utf-8")).hexdigest(),
            )
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
        raise RuntimeError(
            "Encountered an invalid decrypt code, but all exams were "
            "decrypted nevertheless. So, something is crooked!"
        )

    return exam_filenames


def reset() -> None:
    _LOGGER.info("Reseting Abitti2 with a dummy exam package...")
    prepare_exam_package(
        ktp_controller.files.DUMMY_EXAM_PACKAGE_FILEPATH, ["odotusaulakoe"]
    )
    start_decrypted_exams()
    _LOGGER.info("Abitti2 was reset.")


def stop_exam_session(session_uuid: str) -> None:
    _post("/api/end-student-session", data={"sessionUuid": session_uuid})


def download_answers_file(
    dest_filepath: str,
    timeout: int | typing.Tuple[int, int] = (3.1, 20),
) -> str:
    sha256sum = hashlib.sha256()
    with ktp_controller.utils.open_atomic_write(
        dest_filepath, exclusive=True
    ) as dest_file:
        try:
            response = _get(
                "/api/answers-zip/answers.meb", stream=True, timeout=timeout
            )
            for chunk in response.iter_content(4096):
                dest_file.write(chunk)
                sha256sum.update(chunk)
        except requests.exceptions.ConnectTimeout as connect_timeout:
            raise TimeoutError("Connect timed out.") from connect_timeout
        except requests.exceptions.ConnectionError as connection_error:
            # iter_content raises this if underlying read times out.
            if str(connection_error).endswith("Read timed out."):
                raise TimeoutError("Read timed out.") from connection_error
            raise connection_error
        except requests.exceptions.ReadTimeout as read_timeout:
            # requests.get raises this if the response is not returned on time.
            raise TimeoutError("Read timed out.") from read_timeout

    return sha256sum.hexdigest()


def set_exam_session_permission_to_use_browsers(
    session_uuid: str, is_allowed_to_use_browsers: bool
):
    _post(
        "/api/allow-all-browsers",
        data={"allow": is_allowed_to_use_browsers, "sessionUuid": session_uuid},
    )
