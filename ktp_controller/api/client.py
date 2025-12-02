# Standard library imports
import logging
import typing

# Third-party imports
import requests
import requests.exceptions

# Internal imports
import ktp_controller.messages
import ktp_controller.utils
from ktp_controller.settings import SETTINGS
import ktp_controller.api.exam.schemas

__all__ = [
    # Utils:
    "eom_exam_info_to_api_exam_info",
    "get_agent_websock_url",
    "get_ui_websock_url",
    # API commands:
    "async_command",
    "get_current_exam_package",
    "set_current_exam_package_state",
    "get_scheduled_exam",
    "save_exam_info",
    "send_abitti2_status_report",
]


# Constants:


_LOGGER = logging.getLogger(__name__)


# Utils:


def _post(path: str, *, data=None, json=None, timeout: int = 5) -> requests.Response:
    if data is None:
        data = {}
    response = requests.post(
        ktp_controller.utils.get_url(
            f"{SETTINGS.api_host}:{SETTINGS.api_port}", path, scheme="http"
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
    return response


def eom_exam_info_to_api_exam_info(
    eom_exam_info: typing.Dict[str, typing.Any],
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
                "state_changed_at": None,
            }
        )
    return ktp_controller.api.exam.schemas.ExamInfo(
        **{
            "request_id": eom_exam_info["request_id"],
            "scheduled_exams": scheduled_exams,
            "scheduled_exam_packages": scheduled_exam_packages,
            "raw_data": eom_exam_info,
        }
    ).model_dump()


def get_agent_websock_url():
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/system/agent_websocket",
        scheme="ws",
    )


def get_ui_websock_url():
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/system/ui_websocket",
        scheme="ws",
    )


# API commands:


def send_abitti2_status_report(
    abitti2_status_report: typing.Dict,
    *,
    timeout: int = 5,
) -> typing.Any:
    return _post(
        "/api/v1/system/send_abitti2_status_report",
        json=abitti2_status_report,
        timeout=timeout,
    ).json()


def get_last_abitti2_status_report(
    *,
    timeout: int = 5,
) -> typing.Dict[str, typing.Any] | None:
    return _post(
        "/api/v1/system/get_last_abitti2_status_report", timeout=timeout
    ).json()


def get_current_exam_package(*, timeout: int = 20) -> typing.Dict[str, typing.Any]:
    return _post("/api/v1/exam/get_current_exam_package", timeout=timeout).json()


def set_current_exam_package_state(
    external_id: str, state: str, *, timeout: int = 20
) -> str:
    return _post(
        "/api/v1/exam/set_current_exam_package_state",
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


def async_command(command: ktp_controller.messages.Command) -> str:
    return _post("/api/v1/system/async_command", json={"command": command}).json()
