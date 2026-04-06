# Standard library imports
import logging
import typing

# Internal imports
import ktp_controller.httpx
import ktp_controller.messages
import ktp_controller.utils
from ktp_controller import SETTINGS
import ktp_controller.api.exam.schemas
import ktp_controller.api.system.schemas
import ktp_controller.schemas

__all__ = [
    # Utils:
    "eom_exam_info_to_api_exam_info",
    "get_agent_websock_url",
    "get_ui_websock_url",
    # API commands:
    "async_command",
    "get_current_exam_package",
    "get_locked_exam_packages",
    "set_current_exam_package_state",
    "get_scheduled_exam",
    "get_scheduled_exam_package",
    "save_exam_info",
    "send_status_report",
]


_LOGGER = logging.getLogger(__name__)


async def _post(path: str, **kwargs) -> typing.Any:
    kwargs.setdefault("json", {})

    url = ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}", path, scheme="http"
    )

    response = await ktp_controller.httpx.post(url, **kwargs)
    return response.json()


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
                "started_at": None,
                "archived_at": None,
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


def get_agent_websock_url() -> str:
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/system/agent_websocket",
        scheme="ws",
    )


def get_ui_websock_url() -> str:
    return ktp_controller.utils.get_url(
        f"{SETTINGS.api_host}:{SETTINGS.api_port}",
        "/api/v1/system/ui_websocket",
        scheme="ws",
    )


# API commands:


async def send_status_report(status_report: typing.Dict, **kwargs) -> typing.Any:
    kwargs["content"] = (
        ktp_controller.api.system.schemas.StatusReport.model_validate(status_report)
        .model_dump_json(ensure_ascii=True)
        .encode("ascii")
    )
    kwargs["headers"] = {"Content-Type": "application/json"}

    return await _post("/api/v1/system/send_status_report", **kwargs)


async def get_last_status_report(**kwargs) -> typing.Dict[str, typing.Any] | None:
    return await _post("/api/v1/system/get_last_status_report", **kwargs)


async def get_student_access_code() -> ktp_controller.schemas.StudentAccessCode | None:
    last_status_report = await get_last_status_report()
    if last_status_report is None:
        return None

    try:
        student_access_code = last_status_report["abitti2"]["student_access_code"]
    except KeyError:
        # Old reports insert to DB before this commit do not have
        # student_access_code, and it's fine. It's so volatile data
        # afterall that we didn't write data migration for it.
        return None

    if student_access_code is None:
        return None

    return ktp_controller.schemas.StudentAccessCode.model_validate(student_access_code)


async def get_locked_exam_packages(
    **kwargs,
) -> typing.List[typing.Dict[str, typing.Any]]:
    return await _post("/api/v1/exam/get_locked_exam_packages", **kwargs)


async def get_current_exam_package(**kwargs) -> typing.Dict[str, typing.Any]:
    return await _post("/api/v1/exam/get_current_exam_package", **kwargs)


async def set_current_exam_package_state(external_id: str, state: str, **kwargs) -> str:
    kwargs["json"] = {"external_id": external_id, "state": state}

    return await _post("/api/v1/exam/set_current_exam_package_state", **kwargs)


async def get_scheduled_exam(
    external_id: str, **kwargs
) -> typing.Dict[str, typing.Any]:
    kwargs["json"] = {"external_id": external_id}

    return await _post("/api/v1/exam/get_scheduled_exam", **kwargs)


async def save_exam_info(
    eom_exam_info: typing.Dict[str, typing.Any], **kwargs
) -> typing.Any:
    kwargs["json"] = eom_exam_info_to_api_exam_info(eom_exam_info)

    return await _post("/api/v1/exam/save_exam_info", **kwargs)


async def async_command(command: ktp_controller.messages.Command, **kwargs) -> str:
    kwargs["json"] = {"command": command}

    return await _post("/api/v1/system/async_command", **kwargs)


async def get_scheduled_exam_package(
    external_id: str, **kwargs
) -> typing.Dict[str, typing.Any]:
    kwargs["json"] = {"external_id": external_id}

    return await _post("/api/v1/exam/get_scheduled_exam_package", **kwargs)
