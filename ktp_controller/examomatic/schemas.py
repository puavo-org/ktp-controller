# Standard library imports
from typing import Dict, List

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic
import ktp_controller.schemas


__all__ = [
    "StatusReport",
]


class _Abitti2Exam(ktp_controller.pydantic.BaseModel):
    examUuid: pydantic.StrictStr
    examTitle: pydantic.StrictStr
    hasStarted: pydantic.StrictBool
    startTime: ktp_controller.pydantic.DateTime | None
    type: pydantic.StrictStr


class _Abitti2Info(ktp_controller.pydantic.BaseModel):
    domain: pydantic.StrictStr | None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None


class StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: ktp_controller.pydantic.DateTime
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: Dict
    exams: List[_Abitti2Exam] | None
    abitti2: _Abitti2Info
