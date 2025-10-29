# Standard library imports
import hashlib
import logging
import os
import typing

# Third-party imports
import requests
import requests.auth

# Internal imports
import ktp_controller.utils
import ktp_controller.abitti2.naksu2


_LOGGER = logging.getLogger(__name__)


__all__ = [
    # Constants:
    "DUMMY_EXAM_PACKAGE_FILEPATH",
    # Utils:
    "get_basic_auth",
    "get_abitti2_websock_url",
    # Abitti2 API commands:
    "get_current_abitti2_version",
    "get_single_security_code",
    "change_single_security_code",
    "decrypt_exams",
    "load_exam_package",
    "get_decrypted_exams",
    "start_decrypted_exams",
    "reset",
]


# Constants:


_ABITTI2_USERNAME = "valvoja"

DUMMY_EXAM_PACKAGE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/dummy-exam-package.zip"
)


# Utils:


def _get(path: str, *, timeout: int = 20) -> requests.Response:
    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    response = requests.get(
        url,
        auth=requests.auth.HTTPBasicAuth(
            _ABITTI2_USERNAME, ktp_controller.abitti2.naksu2.read_password()
        ),
        timeout=timeout,
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
            _ABITTI2_USERNAME, ktp_controller.abitti2.naksu2.read_password()
        ),
        timeout=timeout,
        json=data,
    )

    response.raise_for_status()

    return response


def get_basic_auth() -> typing.Dict[str, str]:
    return ktp_controller.utils.get_basic_auth(
        _ABITTI2_USERNAME, ktp_controller.abitti2.naksu2.read_password()
    )


def get_abitti2_websock_url():
    return ktp_controller.utils.get_url(
        ktp_controller.abitti2.naksu2.read_domain(),
        "/ws/stats",
        use_tls=True,
        use_websocket=True,
    )


# Abitti2 API commands:


def get_current_abitti2_version() -> str:
    return _get("/api/version").json()["version"]


def get_single_security_code() -> typing.Dict:
    return _get("/api/single-security-code").json()


def change_single_security_code() -> typing.Dict:
    return _post("/api/single-security-code").json()


def decrypt_exams(decrypt_code: str, timeout: int = 60) -> typing.Dict:
    return _post(
        "/api/decrypt-exam", data={"decryptPassword": decrypt_code}, timeout=timeout
    ).json()


def load_exam_package(exam_package_filepath, *, timeout: int = 20) -> typing.Any:
    exam_package_filename = os.path.basename(exam_package_filepath)

    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, "/api/load-exam")

    with open(exam_package_filepath, "rb") as exam_package_file:
        response = requests.post(
            url,
            auth=requests.auth.HTTPBasicAuth(
                _ABITTI2_USERNAME, ktp_controller.abitti2.naksu2.read_password()
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
):
    exam_filenames = set(ktp_controller.abitti2.client.load_exam_package(filepath))

    decrypted_exam_filenames = set()
    had_invalid_decrypt_code = False
    for decrypt_code in decrypt_codes:
        retval = ktp_controller.abitti2.client.decrypt_exams(decrypt_code)
        if retval["wrongPassword"]:
            # TODO: is it ok to expose the decrypt code in log files?
            _LOGGER.error(
                "invalid decrypt code (sha1 hash: %r)",
                hashlib.sha1(decrypt_code.encode("ascii")).hexdigest(),
            )
            had_invalid_decrypt_code = True
        decrypted_exam_filenames.update(retval["mebs"])

    still_encrypted_exam_filenames = exam_filenames - decrypted_exam_filenames

    if len(still_encrypted_exam_filenames) > 0:
        raise RuntimeError(
            f"failed to decrypt {len(still_encrypted_exam_filenames)/len(exam_filenames)} exams",
            still_encrypted_exam_filenames,
        )

    if had_invalid_decrypt_code:
        raise RuntimeError(
            "Encountered an invalid decrypt code, but all exams were "
            "decrypted nevertheless. So, something is crooked!"
        )

    return exam_filenames


def reset() -> typing.List[str]:
    return prepare_exam_package(DUMMY_EXAM_PACKAGE_FILEPATH, ["odotusaulakoe"])


def stop_exam_session(session_uuid: str) -> None:
    _post("/api/end-student-session", data={"sessionUuid": session_uuid})
