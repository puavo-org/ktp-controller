# Standard library imports
from typing import Literal

# Third-party imports
import pydantic
from pydantic import Field

import ktp_controller.api.exam.schemas
import ktp_controller.pydantic
import ktp_controller.schemas
import ktp_controller.settings

# Internal imports
from ktp_controller import VERSION

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
    is_active: pydantic.StrictBool = Field(
        examples=[True, False],
        description="Is the student actively doing the exam. Active students do not have any flags.",
    )
    status: pydantic.StrictStr = Field(examples=["waiting-for-auth-browser"])
    exam_title: pydantic.StrictStr | None = Field(examples=["Odotusaulakoe"])
    has_finished: pydantic.StrictBool = Field(
        examples=[True, False],
        description="Has the student finished the exam. Finished students do not have any flags.",
    )
    flags: set[ktp_controller.schemas.StudentFlag] = Field(
        examples=[
            [ktp_controller.schemas.StudentFlag.IDLE],
            [
                ktp_controller.schemas.StudentFlag.DISCONNECTED,
                ktp_controller.schemas.StudentFlag.UNDEFINED_EXAM,
            ],
        ],
        description="Contains only unique values.",
    )


class _Abitti2ExamStats(ktp_controller.pydantic.BaseModel):
    title: pydantic.StrictStr = Field(examples=["Odotusaulakoe"])
    active_students_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students are active in the exam.", examples=[1]
    )
    finished_students_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students have finished the exam", examples=[0]
    )
    flagged_students_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ...,
        description="How many students have been flagged as having some kind of issue, e.g. disconnected, idle, waiting for authorization, etc.",
        examples=[1],
    )


class _Abitti2Stats(ktp_controller.pydantic.BaseModel):
    exams: list[_Abitti2ExamStats] | None


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
    exams: list[_Exam] | None
    students: list[_Student] | None


class _WebsocketStats(ktp_controller.pydantic.BaseModel):
    connection_duration_current: (
        ktp_controller.pydantic.StrictNonNegativeFloat | None
    ) = Field(
        description="Current connection duration in seconds. Null means there's no connection at the moment."
    )
    connection_duration_mean: ktp_controller.pydantic.StrictNonNegativeFloat | None = (
        Field(
            description="Mean connection duration in seconds since the program start. Null means there has been no connections yet."
        )
    )
    connection_duration_stdev: ktp_controller.pydantic.StrictNonNegativeFloat | None = (
        Field(
            description="Standard deviation of all connection durations in seconds since the program start. Null means there has been no connections yet."
        )
    )
    connection_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        description="Number of connections since the program start."
    )


class _KTPControllerStats(ktp_controller.pydantic.BaseModel):
    abitti2_websocket_stats: _WebsocketStats = Field(
        description="Abitti2 websocket connection statistics"
    )
    api_websocket_stats: _WebsocketStats = Field(
        description="Internal API websocket connection statistics"
    )
    examomatic_websocket_stats: _WebsocketStats = Field(
        description="Exam-O-Matic websocket connection statistics"
    )


class _KTPController(ktp_controller.pydantic.BaseModel):
    # VERSION is a runtime constant; pydantic pins the field to its value.
    version: Literal[VERSION] = VERSION  # type: ignore[valid-type]
    started_at: ktp_controller.pydantic.DateTime = Field(
        description="When the program has started.",
        examples=["2026-05-03T16:28:51.975+0000"],
    )
    is_auto_control_enabled: pydantic.StrictBool = Field(examples=[True])
    cached_files: ktp_controller.schemas.CachedFiles
    current_exam_package: _ExamPackage | None
    next_exam_packages: list[_ExamPackage] | None
    settings: ktp_controller.settings.Settings = Field(
        description="Effective runtime configuation of KTP Controller"
    )
    stats: _KTPControllerStats | None = Field(
        description="All stats are reset when the program starts. If null, there was an error gathering the stats."
    )


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
