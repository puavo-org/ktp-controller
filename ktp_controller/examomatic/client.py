# Standard library imports
import hashlib
import json
import os.path
import typing

# Third-party imports
import requests
import requests.auth

# Internal imports
import ktp_controller.utils
from ktp_controller.settings import SETTINGS


def _get(
    path: str,
    *,
    extra_params: typing.Optional[typing.Dict[str, str]] = None,
    stream: bool = False,
    timeout: int = 20,
) -> requests.Response:
    if extra_params is None:
        extra_params = {}
    params = {
        "domain": SETTINGS.domain,
        "hostname": SETTINGS.hostname,
        "id": SETTINGS.id,
    }
    params.update(extra_params)
    response = requests.get(
        ktp_controller.utils.get_url(SETTINGS.examomatic_host, path),
        auth=requests.auth.HTTPBasicAuth(
            SETTINGS.examomatic_username,
            ktp_controller.utils.readfirstline(
                SETTINGS.examomatic_password_file, encoding="ascii"
            ),
        ),
        params=params,
        timeout=timeout,
        stream=stream,
    )

    response.raise_for_status()

    return response


def _post(path: str, data: bytes, *, timeout: int = 20) -> requests.Response:
    response = requests.post(
        ktp_controller.utils.get_url(
            SETTINGS.examomatic_host,
            path,
        ),
        data=data,
        auth=requests.auth.HTTPBasicAuth(
            SETTINGS.examomatic_username,
            ktp_controller.utils.readfirstline(
                SETTINGS.examomatic_password_file, encoding="ascii"
            ),
        ),
        params={
            "domain": SETTINGS.domain,
            "hostname": SETTINGS.hostname,
            "id": SETTINGS.id,
        },
        timeout=timeout,
    )

    response.raise_for_status()

    return response


def send_abitti2_status_report(
    status_report: typing.Dict, *, timeout: int = 20
) -> typing.Any:
    return _post(
        "/v1/servers/status_update",
        json.dumps(status_report).encode("ascii"),
        timeout=timeout,
    ).json()


def get_exam_info(*, timeout: int = 20) -> typing.Dict:
    return _get("/v2/schedules/exam_packages", timeout=timeout).json()


def get_exam_file_stream(
    sha256sum: str, *, timeout: int = 20, stream_chunk_size=4096
) -> typing.Iterable[bytes]:
    response = _get(
        "/v1/exams/raw_file",
        extra_params={"hash": sha256sum},
        stream=True,
        timeout=timeout,
    )

    sha256sum_of_downloaded_file = hashlib.sha256()

    for chunk in response.iter_content(chunk_size=stream_chunk_size):
        sha256sum_of_downloaded_file.update(chunk)
        yield chunk

    if sha256sum_of_downloaded_file.hexdigest() != sha256sum:
        raise RuntimeError("sha256sum mismatch of downloaded exam file")


def download_exam_file(sha256sum: str, dest_filepath: str, *, timeout: int = 20):
    with ktp_controller.utils.open_atomic_write(
        dest_filepath, exclusive=True
    ) as dest_file:
        for chunk in get_exam_file_stream(sha256sum, timeout=timeout):
            dest_file.write(chunk)


def download_dummy_exam_file(dest_filepath: str, *, timeout: int = 20):
    ktp_controller.utils.copy_atomic(
        os.path.join(os.path.dirname(__file__), "dummy-exam-file.mex"), dest_filepath
    )


def get_basic_auth():
    return ktp_controller.utils.get_basic_auth(
        SETTINGS.examomatic_username,
        ktp_controller.utils.readfirstline(
            SETTINGS.examomatic_password_file, encoding="ascii"
        ),
    )


def websock_get_url():
    return ktp_controller.utils.get_url(
        SETTINGS.examomatic_host,
        "/servers/ers_connection",
        params={
            "domain": SETTINGS.domain,
            "hostname": SETTINGS.hostname,
            "id": SETTINGS.id,
        },
        use_tls=True,
        use_websocket=True,
    )


def websock_validate_message(data):
    message = ktp_controller.utils.json_loads_dict(data)

    if not "type" in message:
        raise ValueError("message does not have 'type'")

    if not isinstance(message["type"], str):
        raise ValueError("message type is not a string")

    if not "id" in message:
        raise ValueError("message does not have 'id'")

    if not isinstance(message["id"], int):
        raise ValueError("message id is not an integer")

    return message


async def websock_ack(websock, message):
    return await ktp_controller.utils.websock_send_json(
        websock, {"type": "ack", "id": message["id"]}
    )
