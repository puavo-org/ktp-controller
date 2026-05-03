# Standard library imports
from typing import Dict, List, Literal

# Third-party imports
import pydantic
from pydantic import Field

# Internal imports
from ktp_controller import VERSION
import ktp_controller.api.exam.schemas
import ktp_controller.pydantic
import ktp_controller.schemas


__all__ = [
    "StatusReport",
]


class _ExamPackage(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr = Field(examples=["b1ce7363-cdd8-4da0-a4f1-ddfe566ffb79"])
    state: ktp_controller.api.exam.schemas.ScheduledExamPackageState | None = Field(
        examples=["running"]
    )
    state_changed_at: ktp_controller.pydantic.DateTime | None = Field(
        examples=["2026-05-03T16:31:24.836+0000"]
    )
    started_at: ktp_controller.pydantic.DateTime | None = Field(
        examples=["2026-05-03T16:31:24.836+0000"]
    )
    archived_at: ktp_controller.pydantic.DateTime | None = Field(
        examples=["2026-05-03T16:32:53.036+0000"]
    )
    scheduled_start_time: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-05-03T16:31:23.036+0000"]
    )
    scheduled_end_time: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-05-03T16:32:53.036+0000"]
    )
    scheduled_lock_time: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-05-03T16:30:53.036+0000"]
    )


class _Exam(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr = Field(examples=["390e7988-ff0e-42b4-a2e6-d13a969e7103"])
    title: pydantic.StrictStr = Field(examples=["Odotusaulakoe"])
    started_at: ktp_controller.pydantic.DateTime | None = Field(
        examples=["2026-05-03T16:29:14.304+0000"]
    )


class _Student(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr = Field(examples=["396d3178-28df-435f-9124-7debdc55111c"])
    session_uuid: pydantic.StrictStr = Field(
        examples=["4fb44768-3193-4e4b-9f3c-e60008362918"]
    )
    is_active: pydantic.StrictBool = Field(examples=[True])
    is_idle: pydantic.StrictBool = Field(examples=[False])
    is_connected: pydantic.StrictBool = Field(examples=[True])
    is_waiting_for_auth: pydantic.StrictBool = Field(examples=[False])
    is_finished: pydantic.StrictBool = Field(examples=[False])
    status: pydantic.StrictStr = Field(examples=["waiting-for-auth-browser"])
    exam_title: pydantic.StrictStr | None = Field(examples=["Odotusaulakoe"])


class _Abitti2ExamStats(ktp_controller.pydantic.BaseModel):
    active_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students are active in the exam", examples=[1]
    )
    idle_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students are idle in the exam", examples=[0]
    )
    gone_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ...,
        description="How many students are gone in a way or another, e.g. disconnected, finished, waiting reauth, etc.",
        examples=[1],
    )


class _Abitti2Stats(ktp_controller.pydantic.BaseModel):
    exams: Dict[str, _Abitti2ExamStats] | None


class _Abitti2(ktp_controller.pydantic.BaseModel):
    stats: _Abitti2Stats
    answer_count: ktp_controller.pydantic.StrictNonNegativeInt | None = Field(
        examples=[1]
    )
    domain: pydantic.StrictStr | None = Field(examples=["ostelu-solmu.koe.abitti.net"])
    student_access_code: ktp_controller.schemas.StudentAccessCode | None
    supervisor_username: pydantic.StrictStr = Field(examples=["valvoja"])
    supervisor_passphrase: pydantic.StrictStr | None = Field(
        examples=["jogurtti lihota vaivutus vigilia"]
    )
    version: pydantic.StrictStr | None = Field(examples=["1.27.0"])
    last_message_received_at: ktp_controller.pydantic.DateTime | None = Field(
        examples=["2026-05-03T16:29:20.007+0000"]
    )
    exams: List[_Exam] | None
    students: List[_Student] | None


class _KTPController(ktp_controller.pydantic.BaseModel):
    version: Literal[VERSION] = VERSION
    started_at: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-05-03T16:28:51.975+0000"]
    )
    is_auto_control_enabled: pydantic.StrictBool = Field(examples=[True])
    cached_files: ktp_controller.schemas.FileStats
    current_exam_package: _ExamPackage | None


class _OSStats(ktp_controller.pydantic.BaseModel):
    disk_usage: list | None = Field(
        examples=[
            [
                {
                    "mountpoint": "/home",
                    "total": 20695207936,
                    "used": 13058498560,
                    "free": 6673039360,
                }
            ]
        ]
    )
    load_average: dict | None = Field(
        examples=[{"1min": 4.9, "5min": 5.0, "15min": 4.7}]
    )
    memory: dict | None = Field(
        examples=[
            {
                "total": 8307036160,
                "used": 4464103424,
                "free": 968290304,
                "available": 3842932736,
            }
        ]
    )
    uptime: float | None = Field(examples=[2425.53])


class _OS(ktp_controller.pydantic.BaseModel):
    stats: _OSStats
    release: pydantic.StrictStr = Field(
        ...,
        description="OS-specific release / version string",
        examples=[
            "O2611 Broom (opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img)"
        ],
    )


class StatusReport(ktp_controller.pydantic.BaseModel):
    v: Literal[2] = 2
    created_at: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-05-03T16:29:20.495+0000"]
    )
    abitti2: _Abitti2
    ktp_controller: _KTPController
    os: _OS
