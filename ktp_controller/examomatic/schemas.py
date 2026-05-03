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
    uuid: pydantic.StrictStr
    state: ktp_controller.api.exam.schemas.ScheduledExamPackageState | None
    state_changed_at: ktp_controller.pydantic.DateTime | None
    started_at: ktp_controller.pydantic.DateTime | None
    archived_at: ktp_controller.pydantic.DateTime | None
    scheduled_start_time: ktp_controller.pydantic.DateTime
    scheduled_end_time: ktp_controller.pydantic.DateTime
    scheduled_lock_time: ktp_controller.pydantic.DateTime


class _Exam(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr
    title: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime | None


class _Student(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr
    session_uuid: pydantic.StrictStr
    is_active: pydantic.StrictBool
    is_idle: pydantic.StrictBool
    is_connected: pydantic.StrictBool
    is_waiting_for_auth: pydantic.StrictBool
    is_finished: pydantic.StrictBool
    status: pydantic.StrictStr
    exam_title: pydantic.StrictStr | None


class _Abitti2ExamStats(ktp_controller.pydantic.BaseModel):
    active_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students are active in the exam"
    )
    idle_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ..., description="How many students are idle in the exam"
    )
    gone_student_count: ktp_controller.pydantic.StrictNonNegativeInt = Field(
        ...,
        description="How many students are gone in a way or another, e.g. disconnected, finished, waiting reauth, etc.",
    )


class _Abitti2Stats(ktp_controller.pydantic.BaseModel):
    exams: Dict[str, _Abitti2ExamStats] | None


class _Abitti2(ktp_controller.pydantic.BaseModel):
    stats: _Abitti2Stats
    answer_count: ktp_controller.pydantic.StrictNonNegativeInt | None
    domain: pydantic.StrictStr | None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None
    supervisor_username: pydantic.StrictStr
    supervisor_passphrase: pydantic.StrictStr | None
    version: pydantic.StrictStr | None
    last_message_received_at: ktp_controller.pydantic.DateTime | None
    exams: List[_Exam] | None
    students: List[_Student] | None


class _KTPController(ktp_controller.pydantic.BaseModel):
    version: Literal[VERSION] = VERSION
    started_at: ktp_controller.pydantic.DateTime
    is_auto_control_enabled: pydantic.StrictBool
    cached_files: ktp_controller.schemas.FileStats
    current_exam_package: _ExamPackage | None


class _OSStats(ktp_controller.pydantic.BaseModel):
    disk_usage: list | None
    load_average: dict | None
    memory: dict | None
    uptime: float | None


class _OS(ktp_controller.pydantic.BaseModel):
    stats: _OSStats
    release: pydantic.StrictStr = Field(
        ..., description="OS-specific release / version string"
    )


class StatusReport(ktp_controller.pydantic.BaseModel):
    v: Literal[2] = 2
    created_at: ktp_controller.pydantic.DateTime
    abitti2: _Abitti2
    ktp_controller: _KTPController
    os: _OS
