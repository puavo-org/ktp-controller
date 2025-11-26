import datetime
import importlib.resources
import json
import typing
import uuid

import ktp_controller.utils


_EXAM_FILE_INFOS = {
    "exam1": {
        "exam_title": "exam1",
        "file_name": "exam1.mex",
        "file_size": 9294014,
        "file_sha256": "fd3a4a6021d4b53daa4494db4b907085917ab542ee10864d426abdf01d5ccc8f",
        "file_uuid": "12cb630c-9419-4fa8-93f7-f1b01779e470",
        "decrypt_code": "kukka ahma reiluus sotaonni",
    },
    "Integraatiotestikoe1": {
        "exam_title": "Integraatiotestikoe1",
        "file_name": "exam_Integraatiotestikoe1.mex",
        "file_size": 25353142,
        "file_sha256": "50d28d5ce4628d9e72c3d42001a49f9fbc146081fbac42610435d6c70d4f6624",
        "file_uuid": "c574f93a-ac4d-4441-8679-ca47e565fb7b",  # UUID from oma.abitti.fi/school/exams
        "decrypt_code": "itarasti toutain edustava myllytys",
    },
}


def get_exam_filepath(filename: str) -> str:
    ktp_controller.utils.check_filename(filename)
    return str(
        importlib.resources.files(
            "ktp_controller.examomatic.mock.data.exam_files"
        ).joinpath(filename)
    )


def read_exam_info(filename: str) -> typing.Dict[str, typing.Any]:
    ktp_controller.utils.check_filename(filename)
    return json.loads(
        importlib.resources.files("ktp_controller.examomatic.mock.data.exam_infos")
        .joinpath(filename)
        .read_text()
    )


def get_synthetic_exam_info(
    *,
    start_time: datetime.datetime | None = None,
    utcnow: datetime.datetime | None = None,
    lock_time_duration: datetime.timedelta | None = None,
    duration: datetime.timedelta | None = None,
    server_id: int = 2,
    exam_title: str = "exam1",
) -> typing.Dict[str, typing.Any]:
    if utcnow is None:
        utcnow = ktp_controller.utils.utcnow()
    if duration is None:
        duration = datetime.timedelta(minutes=30)
    if lock_time_duration is None:
        lock_time_duration = datetime.timedelta(minutes=15)
    if start_time is None:
        start_time = utcnow + lock_time_duration

    exam_uuid = str(uuid.uuid4())
    exam_package_uuid = str(uuid.uuid4())
    end_time = start_time + duration
    lock_time = start_time - lock_time_duration

    exam_schedule = {
        "id": exam_uuid,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "exam_modified_at": (start_time - datetime.timedelta(hours=1)).isoformat(),
        "schedule_modified_at": (
            start_time - datetime.timedelta(minutes=30)
        ).isoformat(),
        "school_name": "school1",
        "server_id": server_id,
        "is_retake": False,
        "retake_participants": 0,
    }

    exam_schedule.update(_EXAM_FILE_INFOS[exam_title])

    return json.loads(
        json.dumps(
            {
                "schedules": [
                    exam_schedule,
                ],
                "packages": {
                    exam_package_uuid: {
                        "id": exam_package_uuid,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "lock_time": lock_time.isoformat(),
                        "schedules": [exam_uuid],
                        "locked": utcnow >= lock_time,
                        "server_id": server_id,
                        "estimated_total_size": 0,
                    },
                },
                "request_id": str(uuid.uuid4()),
            }
        )
    )
