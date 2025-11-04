# Standard library imports
import contextlib
import datetime
import logging
import os.path
import typing
import uuid

# Third-party imports
import fastapi  # type: ignore
import fastapi.responses
import uvicorn  # type: ignore
import pydantic

# Internal imports
import ktp_controller.pydantic


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
    yield
    _LOGGER.info("Stopping...")


APP = fastapi.FastAPI(lifespan=_lifespan)


_g_data_dir = None


def _exam_file_streamer(sha256):
    with open(os.path.join(_g_data_dir, "exam-files", sha256.lower()), "rb") as f:
        while True:
            data = f.read(4096)
            if not data:
                break
            yield data


@APP.get(
    "/v1/exams/raw_file",
    response_model=None,
    status_code=200,
)
def _get_exam_file_stream(
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: str = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
    sha256sum: pydantic.constr(
        strict=True, pattern=r"^[0-9a-fA-F]{64}$"
    ) = fastapi.Query(..., alias="hash"),
):
    # For usability, user wanting to use this Exam-O-Matic mock needs
    # to explicitly claim it.
    if domain != "integration.test":
        raise fastapi.HTTPException(400, detail="domain must be integration.test")

    return fastapi.responses.StreamingResponse(
        _exam_file_streamer(sha256sum), media_type="application/zip"
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
    server_id: typing.List[pydantic.conint(strict=True, ge=1)]
    is_retake: pydantic.StrictBool
    retake_participants: pydantic.conint(strict=True, ge=0)


class _Package(ktp_controller.pydantic.BaseModel):
    id_: pydantic.StrictStr = pydantic.Field(..., alias="id")
    start_time: datetime.datetime
    end_time: datetime.datetime
    lock_time: datetime.datetime
    schedules: typing.List[pydantic.StrictStr]
    locked: pydantic.StrictBool
    server_id: pydantic.conint(strict=True, ge=1)
    estimated_total_size: pydantic.conint(strict=True, ge=0)


class _ExamInfo(ktp_controller.pydantic.BaseModel):
    schedules: typing.List[_Schedule]
    packages: typing.Dict[str, _Package]
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
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "exam_modified_at": utcnow.isoformat(),
                "schedule_modified_at": utcnow.isoformat(),
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
        "request_id": f"{domain} {hostname} {server_id} {utcnow.isoformat()} {str(uuid.uuid4())}",
    }


_TEST_DATA_FUNCTIONS = {
    "single_exam_package": _get_exam_info_single_exam_package,
}


@APP.get(
    "/v2/schedules/exam_packages",
    response_model=_ExamInfo,
    status_code=200,
)
def _get_exam_info(
    domain: str, hostname: str, server_id: int = fastapi.Query(..., alias="id")
):
    # For usability, user wanting to use this Exam-O-Matic mock needs
    # to explicitly claim it.
    if domain != "integration.test":
        raise fastapi.HTTPException(400, detail="domain must be integration.test")

    utcnow = datetime.datetime.utcnow()

    # We try to be clever here and let the caller select the test case
    # data with hostname parameter.
    try:
        test_data_func = _TEST_DATA_FUNCTIONS[hostname]
    except KeyError as key_error:
        raise fastapi.HTTPException(
            404,
            detail=f"available hostnames (test data sets): {list(_TEST_DATA_FUNCTIONS.keys())}",
        ) from key_error

    return test_data_func(domain, hostname, server_id, utcnow)


class _Abitti2StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: datetime.datetime
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict


@APP.post(
    "/v1/servers/status_update",
    response_model=None,
    status_code=200,
)
def _send_abitti2_status_report(
    request: _Abitti2StatusReport,  # pylint: disable=unused-argument
    domain: str,
    hostname: str,  # pylint: disable=unused-argument
    server_id: int = fastapi.Query(..., alias="id"),  # pylint: disable=unused-argument
):
    # For usability, user wanting to use this Exam-O-Matic mock needs
    # to explicitly claim it.
    if domain != "integration.test":
        raise fastapi.HTTPException(400, detail="domain must be integration.test")


def run(port: int, data_dir: str):
    global _g_data_dir
    if _g_data_dir is None:
        _g_data_dir = data_dir
    else:
        raise RuntimeError("_DATA_DIR is already set")

    uvicorn.run(
        "ktp_controller.examomatic.mock.main:APP",
        host="127.0.0.1",
        port=port,
        reload=False,
    )
