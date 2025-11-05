# Standard library imports
import datetime
import json
import sys
import time
import uuid

# Third-party imports
import requests.exceptions

# Internal imports
import ktp_controller.examomatic.client
from ktp_controller.settings import SETTINGS


def get_eom_exam_info_single_exam_package(
    *,
    domain: str = SETTINGS.domain,
    hostname: str = SETTINGS.hostname,
    server_id: int = SETTINGS.id,
    utcnow: datetime.datetime = None,
):
    if utcnow is None:
        utcnow = datetime.datetime.utcnow()

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
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "lock_time": lock_time.isoformat(),
                "schedules": [exam_uuid],
                "locked": start_time >= lock_time,
                "server_id": server_id,
                "estimated_total_size": 25356295,
            },
        },
        "request_id": f"{domain} {hostname} {server_id} {utcnow.isoformat()} {str(uuid.uuid4())}",
    }


def test_single_exam_package():
    eom_exam_info = get_eom_exam_info_single_exam_package()

    ktp_controller.examomatic.client._post(
        "/mock/setup_exam_info",
        data=json.dumps(eom_exam_info, ensure_ascii=True).encode("ascii"),
    )

    agent_has_called_home = False
    for i in range(5):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["pong_count"] > 1:
            agent_has_called_home = True
            break
        time.sleep(1)
    assert agent_has_called_home

    # assert (
    #     ktp_controller.examomatic.client._post("/mock/get_state").json()[
    #         "status_reports"
    #     ]
    #     == {}
    # )
