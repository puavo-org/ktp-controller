# Standard library imports
import asyncio
import contextlib
import datetime
import hashlib
import logging
import uuid

from typing import Annotated, Dict, List, Any

# Third-party imports
import fastapi  # type: ignore
import fastapi.responses
import uvicorn  # type: ignore
import pydantic

# Internal imports
import ktp_controller.pydantic
import ktp_controller.utils

from .utils import get_exam_filepath


__all__ = [
    # Constants:
    "APP",
    # Interface:
    "run",
]


# Constants:

_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI):  # pylint: disable=unused-argument
    _LOGGER.info("Starting...")
    app.state.is_running = True
    yield
    app.state.is_running = False
    _LOGGER.info("Stopping...")


def _check_domain(domain: str):
    # For safety and user-friendlyness, user wanting to use this
    # Exam-O-Matic mock needs to explicitly claim it.
    if domain != "integration.test":
        raise fastapi.HTTPException(400, detail="domain must be integration.test")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.state.exam_infos = {}
APP.state.do_send_refresh_exams = False
APP.state.is_running = False
APP.state.status_reports = {}
APP.state.request_counts = {}
APP.state.pong_count = 0
APP.state.ack_count = 0
APP.state.refresh_exams_count = 0
APP.state.data = {}


@APP.get(
    "/v1/exams/raw_file",
    response_model=None,
    status_code=200,
)
async def _get_exam_file_stream(
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: str = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
    sha256sum: ktp_controller.pydantic.StrictSHA256String = fastapi.Query(
        ..., alias="hash"
    ),
):
    _check_domain(domain)
    return await fastapi.responses.StreamingResponse(
        ktp_controller.utils.bytes_stream(get_exam_filepath(sha256sum)),
        media_type="application/zip",
    )


class _Schedule(ktp_controller.pydantic.BaseModel):
    id_: pydantic.StrictStr = pydantic.Field(..., alias="id")
    exam_title: pydantic.StrictStr
    file_name: pydantic.StrictStr
    file_size: pydantic.conint(strict=True, ge=0)
    file_sha256: pydantic.StrictStr
    file_uuid: pydantic.StrictStr
    decrypt_code: pydantic.StrictStr
    start_time: datetime.datetime
    end_time: datetime.datetime
    exam_modified_at: datetime.datetime
    schedule_modified_at: datetime.datetime
    school_name: pydantic.StrictStr
    server_id: List[pydantic.conint(strict=True, ge=1)]
    is_retake: pydantic.StrictBool
    retake_participants: pydantic.conint(strict=True, ge=0)


class _Package(ktp_controller.pydantic.BaseModel):
    id_: pydantic.StrictStr = pydantic.Field(..., alias="id")
    start_time: datetime.datetime
    end_time: datetime.datetime
    lock_time: datetime.datetime
    schedules: List[pydantic.StrictStr]
    locked: pydantic.StrictBool
    server_id: pydantic.conint(strict=True, ge=1)
    estimated_total_size: pydantic.conint(strict=True, ge=0)


class _ExamInfo(ktp_controller.pydantic.BaseModel):
    schedules: List[_Schedule]
    packages: Dict[str, _Package]
    request_id: pydantic.StrictStr


def _get_exam_info_single_exam_package(
    domain: str, hostname: str, server_id: int, utcnow: datetime.datetime
):
    start_time = utcnow + datetime.timedelta(minutes=2)
    end_time = start_time + datetime.timedelta(minutes=1)
    lock_time = start_time - datetime.timedelta(minutes=1)

    exam_uuid: str = str(uuid.uuid4())
    package_uuid: str = str(uuid.uuid4())

    return {
        "schedules": [
            {
                "id": exam_uuid,
                "exam_title": "Integraatiotestikoe1",
                "file_name": "exam_Integraatiotestikoe1.mex",
                "file_size": 25353142,
                "file_sha256": "50d28d5ce4628d9e72c3d42001a49f9fbc146081fbac42610435d6c70d4f6624",
                "file_uuid": "c574f93a-ac4d-4441-8679-ca47e565fb7b",  # UUID from oma.abitti.fi/school/exams
                "decrypt_code": "itarasti toutain edustava myllytys",
                "start_time": ktp_controller.utils.strfdt(start_time),
                "end_time": ktp_controller.utils.strfdt(end_time),
                "exam_modified_at": ktp_controller.utils.strfdt(utcnow),
                "schedule_modified_at": ktp_controller.utils.strfdt(utcnow),
                "school_name": f"{domain} school",
                "server_id": [server_id],
                "is_retake": False,
                "retake_participants": 0,
            },
        ],
        "packages": {
            package_uuid: {
                "id": package_uuid,
                "start_time": start_time,
                "end_time": end_time,
                "lock_time": lock_time,
                "schedules": [exam_uuid],
                "locked": start_time >= lock_time,
                "server_id": server_id,
                "estimated_total_size": 25356295,
            },
        },
        "request_id": f"{domain} {hostname} {server_id} {ktp_controller.utils.strfdt(utcnow)} {str(uuid.uuid4())}",
    }


_TEST_DATA_FUNCTIONS = {
    "single_exam_package": _get_exam_info_single_exam_package,
}


class _Abitti2StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: datetime.datetime
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: Dict


@APP.post(
    "/mock/setup_exam_info",
    response_model=None,
    status_code=200,
)
async def _mock_setup_exam_info(
    exam_info: _ExamInfo,
    domain: str,
    hostname: str,
    server_id: int = fastapi.Query(..., alias="id"),
):
    _check_domain(domain)

    APP.state.exam_infos[(domain, hostname, server_id)] = exam_info.model_dump()
    APP.state.do_send_refresh_exams = True


@APP.post(
    "/mock/get_state",
    response_model=Dict[str, Any],
    status_code=200,
)
async def _mock_get_state(
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: int = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
):
    _check_domain(domain)

    return APP.state._state  # pylint: disable=protected-access


@APP.get(
    "/v2/schedules/exam_packages",
    response_model=_ExamInfo,
    status_code=200,
)
async def _get_exam_info(
    domain: str, hostname: str, server_id: int = fastapi.Query(..., alias="id")
):
    utcnow = datetime.datetime.utcnow()

    _check_domain(domain)

    APP.state.request_counts.setdefault(
        (domain, hostname, server_id), {"get_exam_info": 0}
    )["get_exam_info"] += 1

    try:
        exam_info = APP.state.exam_infos[(domain, hostname, server_id)]
    except KeyError as key_error:
        raise fastapi.HTTPException(404) from key_error

    exam_info["request_id"] = (
        f"{domain} {hostname} {server_id} {utcnow.isoformat()} {str(uuid.uuid4())}"
    )

    return exam_info


@APP.post(
    "/v1/servers/status_update",
    response_model=None,
    status_code=200,
)
async def _send_abitti2_status_report(
    request: _Abitti2StatusReport,  # pylint: disable=unused-argument
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: int = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
):
    _check_domain(domain)

    APP.state.status_reports.setdefault((domain, hostname, server_id), []).append(
        request.model_dump()
    )


@APP.post(
    "/v1/answers/upload",
    response_model=None,
    status_code=200,
)
def _upload_answers_file(
    *,
    answers_file: Annotated[fastapi.UploadFile, fastapi.File()],
    file_sha256: Annotated[str, fastapi.Form()],
    file_size: Annotated[int, fastapi.Form()],
    package_id: Annotated[str, fastapi.Form()],  # pylint: disable=unused-argument
    is_final: Annotated[str, fastapi.Form()],
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: int = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
):
    _check_domain(domain)

    if answers_file.size != file_size:
        raise fastapi.HTTPException(
            400,
            detail=f"incorrect file_size, expected {answers_file.size}, got {file_size}",
        )

    expected_sha256 = hashlib.sha256(answers_file.file.read()).hexdigest()
    if expected_sha256 != file_sha256:
        raise fastapi.HTTPException(
            400,
            detail=f"incorrect file_sha256, expected {expected_sha256}, got {file_sha256}",
        )

    if is_final not in ("false", "true", "unknown"):
        raise fastapi.HTTPException(400, detail=f"incorrect is_final: {is_final!r}")


async def _play_ping_pong_with_ktp_controller(websock: fastapi.WebSocket):
    async for message in websock.iter_json():
        if message["type"] == "ping":
            APP.state.pong_count += 1
            await websock.send_json({"type": "pong", "id": 1})
            _LOGGER.info(
                "Responded successfully to ping #%d with pong.", APP.state.pong_count
            )
            continue
        if message["type"] == "ack":
            APP.state.ack_count += 1
            _LOGGER.info("Received ack: %s", message)
            continue
        _LOGGER.warning("Received and ignored unknown message: %s", message)


async def _send_refresh_exams(websock: fastapi.WebSocket):
    while APP.state.is_running:
        if APP.state.do_send_refresh_exams:
            APP.state.do_send_refresh_exams = False
            APP.state.refresh_exams_count += 1
            await websock.send_json({"type": "refresh_exams", "id": 1})
            _LOGGER.info("Sent refresh_exams #%d.", APP.state.refresh_exams_count)
        await asyncio.sleep(1)


@APP.websocket("/servers/ers_connection")
async def _ktp_controller_websocket(
    websock: fastapi.WebSocket,
    domain: str,  # pylint: disable=unused-argument
    hostname: str,  # pylint: disable=unused-argument
    server_id: int = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
):
    try:
        _check_domain(domain)
    except fastapi.exceptions.HTTPException as e:
        await websock.close(1008, e.detail)

    await websock.accept()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_play_ping_pong_with_ktp_controller(websock))
        tg.create_task(_send_refresh_exams(websock))


def run(port: int):
    uvicorn.run(
        "ktp_controller.examomatic.mock.main:APP",
        host="127.0.0.1",
        port=port,
        reload=False,
    )
