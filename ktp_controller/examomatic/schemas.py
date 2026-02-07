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
    uuid: pydantic.StrictStr
    title: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime | None


class _Abitti2Info(ktp_controller.pydantic.BaseModel):
    domain: pydantic.StrictStr | None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None
    supervisor_username: pydantic.StrictStr
    supervisor_passphrase: pydantic.StrictStr | None
    version: pydantic.StrictStr | None
    last_message_received_at: ktp_controller.pydantic.DateTime | None
    exams: List[_Abitti2Exam] | None


class StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: ktp_controller.pydantic.DateTime
    monitoring_passphrase: (
        pydantic.StrictStr
    )  # TODO: remove when Exam-O-Matic reads abitti2.supervisor_passphrase
    status: Dict
    abitti2: _Abitti2Info
