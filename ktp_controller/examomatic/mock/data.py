import datetime
import json
import uuid

import ktp_controller.utils

REAL_ANONYMIZED_EOM_EXAM_INFO_JSON = """
{
  "schedules": [
    {
      "id": "5db14454-8d68-47af-9e23-e1bb45170d89",
      "exam_title": "exam1",
      "file_name": "exam1.mex",
      "file_size": 9294014,
      "file_sha256": "fd3a4a6021d4b53daa4494db4b907085917ab542ee10864d426abdf01d5ccc8f",
      "file_uuid": "12cb630c-9419-4fa8-93f7-f1b01779e470",
      "decrypt_code": "kukka ahma reiluus sotaonni",
      "start_time": "2025-05-28T05:00:00.000+0000",
      "end_time": "2025-05-28T10:00:00.000+0000",
      "exam_modified_at": "2025-05-26T08:48:22.000+0000",
      "schedule_modified_at": "2025-05-26T08:48:22.000+0000",
      "school_name": "school1",
      "server_id": [
        2
      ],
      "is_retake": false,
      "retake_participants": 0
    },
    {
      "id": "fe20d1cb-c30d-47f4-88b1-3e7dd492d061",
      "exam_title": "exam2",
      "file_name": "exam2.mex",
      "file_size": 25416803,
      "file_sha256": "1c5fa27f0f2b4e6254c581a40bdba29abe5ecd4fda966922710e84e7915450c9",
      "file_uuid": "6b9674b8-0875-4b20-a41e-264594e5c2c8",
      "decrypt_code": "decryptcode something",
      "start_time": "2025-05-28T05:00:00.000+0000",
      "end_time": "2025-05-28T09:30:00.000+0000",
      "exam_modified_at": "2025-05-18T11:09:50.000+0000",
      "schedule_modified_at": "2025-05-18T11:09:50.000+0000",
      "school_name": "school1",
      "server_id": [
        2
      ],
      "is_retake": false,
      "retake_participants": 0
    },
    {
      "id": "b57445c4-5262-4095-bc9f-92c95cbf6d2b",
      "exam_title": "exam3",
      "file_name": "exam3.mex",
      "file_size": 9350910,
      "file_sha256": "cbf32ff44b86621e8e5bf52f027d08571646848c749f7bee265dc7a3519026c7",
      "file_uuid": "b09ef59d-1a89-4fe8-acaf-e749d46de059",
      "decrypt_code": "bad code",
      "start_time": "2025-05-28T11:45:00.000+0000",
      "end_time": "2025-05-28T16:45:00.000+0000",
      "exam_modified_at": "2025-05-26T12:10:02.000+0000",
      "schedule_modified_at": "2025-05-26T12:10:02.000+0000",
      "school_name": "school1",
      "server_id": [
        2
      ],
      "is_retake": false,
      "retake_participants": 0
    }
  ],
  "packages": {
    "49cdca0d-3d77-4fe1-a69b-b89a7ddf46f0": {
      "id": "49cdca0d-3d77-4fe1-a69b-b89a7ddf46f0",
      "start_time": "2025-05-28T05:00:00.000+0000",
      "end_time": "2025-05-28T11:15:00.000+0000",
      "lock_time": "2025-05-28T04:45:00.000+0000",
      "schedules": [
        "5db14454-8d68-47af-9e23-e1bb45170d89",
        "fe20d1cb-c30d-47f4-88b1-3e7dd492d061"
      ],
      "locked": true,
      "server_id": 2,
      "estimated_total_size": 0
    },
    "75814ba0-39d9-4818-bdba-6527e691434b": {
      "id": "75814ba0-39d9-4818-bdba-6527e691434b",
      "start_time": "2025-05-28T11:45:00.000+0000",
      "end_time": "2025-05-28T17:15:00.000+0000",
      "lock_time": "2025-05-28T11:30:00.000+0000",
      "schedules": [
        "b57445c4-5262-4095-bc9f-92c95cbf6d2b"
      ],
      "locked": true,
      "server_id": 2,
      "estimated_total_size": 0
    }
  },
  "request_id": "REQ1"
}
"""


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


def get_synthetic_exam_info(
    *,
    start_time: datetime.datetime | None = None,
    utcnow: datetime.datetime | None = None,
    lock_time_duration: datetime.timedelta | None = None,
    duration: datetime.timedelta | None = None,
    server_id: int = 2,
    exam_title: str = "exam1",
):
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
