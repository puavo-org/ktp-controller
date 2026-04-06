# Standard library imports
import enum
import hashlib
import logging
import os.path
import typing

# Third-party imports
import httpx

# Internal imports
import ktp_controller.examomatic.schemas
import ktp_controller.httpx
import ktp_controller.utils
from ktp_controller import SETTINGS

_LOGGER = logging.getLogger(__file__)

__all__ = [
    # Utils:
    "get_basic_auth",
    "get_examomatic_websock_url",
    "websock_validate_message",
    # Exam-O-Matic API commands:
    "send_status_report",
    "get_exam_info",
    "get_exam_file_stream",
    "download_exam_file",
    "download_dummy_exam_file",
    "websock_ack",
    "upload_answers_file",
]


def _get_auth() -> typing.Optional[typing.Tuple[str, str]]:
    if SETTINGS.examomatic_username and SETTINGS.examomatic_password_file:
        return (
            SETTINGS.examomatic_username,
            ktp_controller.utils.readfirstline(
                SETTINGS.examomatic_password_file, encoding="utf-8"
            ),
        )
    return None


async def _get(path: str, **kwargs) -> httpx.Response:
    params = {
        "domain": SETTINGS.domain,
        "hostname": SETTINGS.hostname,
        "id": SETTINGS.id,
    }

    url = ktp_controller.utils.get_url(
        SETTINGS.examomatic_host,
        path,
        params=params,
        scheme="https" if SETTINGS.examomatic_use_tls else "http",
    )

    kwargs["auth"] = _get_auth()

    return await ktp_controller.httpx.get(url, **kwargs)


async def _post(path: str, **kwargs) -> httpx.Response:
    url = ktp_controller.utils.get_url(
        SETTINGS.examomatic_host,
        path,
        scheme="https" if SETTINGS.examomatic_use_tls else "http",
    )

    kwargs["params"] = {
        "domain": SETTINGS.domain,
        "hostname": SETTINGS.hostname,
        "id": SETTINGS.id,
    }

    return await ktp_controller.httpx.post(url, **kwargs)


def get_basic_auth() -> typing.Dict[str, str]:
    if SETTINGS.examomatic_username and SETTINGS.examomatic_password_file:
        return ktp_controller.utils.get_basic_auth(
            SETTINGS.examomatic_username,
            ktp_controller.utils.readfirstline(
                SETTINGS.examomatic_password_file, encoding="utf-8"
            ),
        )
    return {}


def get_examomatic_websock_url():
    return ktp_controller.utils.get_url(
        SETTINGS.examomatic_host,
        "/servers/ers_connection",
        params={
            "domain": SETTINGS.domain,
            "hostname": SETTINGS.hostname,
            "id": SETTINGS.id,
        },
        scheme="wss" if SETTINGS.examomatic_use_tls else "ws",
    )


def websock_validate_message(data):
    message = ktp_controller.utils.json_loads_dict(data)

    if "type" not in message:
        raise ValueError("message does not have 'type'")

    if not isinstance(message["type"], str):
        raise ValueError("message type is not a string")

    if "id" not in message:
        raise ValueError("message does not have 'id'")

    if not isinstance(message["id"], int):
        raise ValueError("message id is not an integer")

    return message


# Exam-O-Matic API commands:


async def send_status_report(status_report: typing.Dict, **kwargs) -> typing.Any:
    kwargs["content"] = (
        ktp_controller.examomatic.schemas.StatusReport.model_validate(status_report)
        .model_dump_json(ensure_ascii=True)
        .encode("ascii")
    )
    kwargs["headers"] = {"Content-Type": "application/json"}

    response = await _post("/v1/servers/status_update", **kwargs)
    return response.json()


async def get_exam_info(**kwargs) -> typing.Dict:
    response = await _get("/v2/schedules/exam_packages", **kwargs)
    return response.json()


async def get_exam_file_stream(sha256sum: str, **kwargs) -> typing.AsyncIterable[bytes]:
    url = ktp_controller.utils.get_url(
        SETTINGS.examomatic_host,
        "/v1/exams/raw_file",
        scheme="https" if SETTINGS.examomatic_use_tls else "http",
    )

    kwargs["params"] = {
        "domain": SETTINGS.domain,
        "hostname": SETTINGS.hostname,
        "id": SETTINGS.id,
        "hash": sha256sum,
    }
    kwargs["auth"] = _get_auth()
    kwargs["chunk_size"] = 4096

    sha256sum_of_downloaded_file = hashlib.sha256()

    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, **kwargs) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                await response.aread()
                if response.text:
                    _LOGGER.error("error content: %s", response.text)
                raise

            async for chunk in response.aiter_bytes(chunk_size=4096):
                sha256sum_of_downloaded_file.update(chunk)
                yield chunk

    if sha256sum_of_downloaded_file.hexdigest() != sha256sum:
        raise RuntimeError("sha256sum mismatch of downloaded exam file")


async def download_exam_file(sha256sum: str, dest_filepath: str, **kwargs):
    with ktp_controller.utils.open_atomic_write(
        dest_filepath, exclusive=True
    ) as dest_file:
        async for chunk in get_exam_file_stream(sha256sum, **kwargs):
            dest_file.write(chunk)


def download_dummy_exam_file(dest_filepath: str, **kwargs):
    # This remains sync as it is doing a local file copy operation
    ktp_controller.utils.copy_atomic(
        os.path.join(os.path.dirname(__file__), "dummy-exam-file.mex"), dest_filepath
    )


async def websock_ack(websock, message):
    return await ktp_controller.utils.websock_send_json(
        websock, {"type": "ack", "id": message["id"]}
    )


class IsFinal(str, enum.Enum):
    FALSE = "false"
    TRUE = "true"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> bool:
        return self.value == self.TRUE


async def upload_answers_file(
    *,
    exam_package_external_id: str,
    filepath: str,
    sha256sum: str | None = None,
    is_final: IsFinal = IsFinal.UNKNOWN,
    **kwargs,
):
    is_final = IsFinal(is_final)

    if sha256sum is None:
        sha256sum = ktp_controller.utils.sha256(filepath)

    filename = os.path.basename(filepath)

    with open(filepath, "rb") as f:
        file_size = f.seek(0, 2)
        f.seek(0)

        kwargs["data"] = {
            "answers_file": filename,
            "file_sha256": sha256sum,
            "file_size": str(file_size),
            "is_final": is_final.value,
            "package_id": exam_package_external_id,
        }
        kwargs["files"] = {"answers_file": f}

        await _post("/v1/answers/upload", **kwargs)
