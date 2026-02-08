# Standard library imports
from typing import List, Literal

# Third-party imports
import pydantic

# Internal imports
from ktp_controller import VERSION
import ktp_controller.pydantic
import ktp_controller.schemas


__all__ = [
    "StatusReport",
]


class _Exam(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr
    title: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime | None


class _Student(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.StrictStr
    session_uuid: pydantic.StrictStr
    is_active: pydantic.StrictBool
    status: pydantic.StrictStr


class _Abitti2(ktp_controller.pydantic.BaseModel):
    answer_count: ktp_controller.pydantic.StrictNonNegativeInt
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


class StatusReport(ktp_controller.pydantic.BaseModel):
    v: Literal[1] = 1
    created_at: ktp_controller.pydantic.DateTime
    abitti2: _Abitti2
    ktp_controller: _KTPController
