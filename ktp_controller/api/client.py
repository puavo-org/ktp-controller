# Standard library imports
import logging
import typing

# Third-party imports
import requests
import requests.exceptions
import websockets

# Internal imports
import ktp_controller.utils
from ktp_controller.settings import SETTINGS


__all__ = [
    "async_enable_auto_control",
    "async_disable_auto_control",
    "eom_exam_info_to_api_exam_info",
    "get_current_scheduled_exam_package",
    "get_scheduled_exam",
    "get_scheduled_exam_packages",
    "save_exam_info",
    "send_abitti2_status_report",
    "set_current_scheduled_exam_package_state",
    "get_agent_websock_url",
]

_LOGGER = logging.getLogger(__name__)


def _post(path: str, *, data=None, json=None, timeout: int = 5) -> requests.Response:
    if data is None:
        data = {}
    response = requests.post(
        ktp_controller.utils.get_url(
            f"{SETTINGS.api_host}:{SETTINGS.api_port}", path, use_tls=False
        ),
        data=data,
        json=json,
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_error:
        _LOGGER.exception("POST failed: %s", http_error.response.content)
        raise
    return response.json()


def send_abitti2_status_report(
    abitti2_status_report: typing.Dict,
    *,
    timeout: int = 5,
) -> typing.Any:
    return _post(
        "/api/v1/abitti2/send_status_report",
        json=abitti2_status_report,
        timeout=timeout,
    )


def eom_exam_info_to_api_exam_info(
    eom_exam_info: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    scheduled_exams = []
    for schedule in eom_exam_info["schedules"]:
        scheduled_exams.append(
            {
                "external_id": schedule["id"],
                "modified_at": schedule["schedule_modified_at"],
                "exam_title": schedule["exam_title"],
                "start_time": schedule["start_time"],
                "end_time": schedule["end_time"],
                "exam_file_info": {
                    "external_id": schedule["file_uuid"],
                    "name": schedule["file_name"],
                    "sha256": schedule["file_sha256"],
                    "size": schedule["file_size"],
                    "decrypt_code": schedule["decrypt_code"],
                    "modified_at": schedule["exam_modified_at"],
                },
            }
        )

    scheduled_exam_packages = []
    for external_id, package in eom_exam_info["packages"].items():
        scheduled_exam_packages.append(
            {
                "external_id": external_id,
                "start_time": package["start_time"],
                "end_time": package["end_time"],
                "lock_time": package["lock_time"],
                "locked": package["locked"],
                "scheduled_exam_external_ids": package["schedules"],
                "state": None,
            }
        )
    return {
        "request_id": eom_exam_info["request_id"],
        "scheduled_exams": scheduled_exams,
        "scheduled_exam_packages": scheduled_exam_packages,
        "raw_data": eom_exam_info,
    }


def get_scheduled_exam_packages(
    *, timeout: int = 20
) -> typing.List[typing.Dict[str, typing.Any]]:
    return _post("/api/v1/exam/get_scheduled_exam_packages", timeout=timeout).json()


def get_current_scheduled_exam_package(
    *, timeout: int = 20
) -> typing.Dict[str, typing.Any]:
    return _post(
        "/api/v1/exam/get_current_scheduled_exam_package", timeout=timeout
    ).json()


def set_current_scheduled_exam_package_state(
    external_id: str, state: str, *, timeout: int = 20
) -> str:
    return _post(
        "/api/v1/exam/set_current_scheduled_exam_package_state",
        json={"external_id": external_id, "state": state},
        timeout=timeout,
    ).json()


def get_scheduled_exam(
    external_id: str, *, timeout: int = 20
) -> typing.Dict[str, typing.Any]:
    return _post(
        "/api/v1/exam/get_scheduled_exam",
        json={"external_id": external_id},
        timeout=timeout,
    ).json()


def save_exam_info(
    eom_exam_info: typing.Dict[str, typing.Any], *, timeout: int = 5
) -> typing.Any:
    return _post(
        "/api/v1/exam/save_exam_info",
        json=eom_exam_info_to_api_exam_info(eom_exam_info),
        timeout=timeout,
    ).json()


def get_agent_websock_url():
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/agent/websocket",
        use_tls=False,
        use_websocket=True,
    )


def get_ui_websock_url():
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/ui/websocket",
        use_tls=False,
        use_websocket=True,
    )


async def connect_ui_websock() -> websockets.connect:
    return await websockets.connect(get_ui_websock_url())


def async_enable_auto_control() -> str:
    return _post("/api/v1/ui/async_enable_auto_control").json()


def async_disable_auto_control() -> str:
    return _post("/api/v1/ui/async_disable_auto_control").json()
