# Standard library imports
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

# Relative imports


__all__ = [
    # Types:
    "Abitti2Exam",
    "Abitti2StatusReport",
]


# Types:


class Abitti2Exam(ktp_controller.pydantic.BaseModel):
    examUuid: pydantic.StrictStr
    examTitle: pydantic.StrictStr
    hasStarted: pydantic.StrictBool
    startTime: ktp_controller.pydantic.DateTime | None
    type: pydantic.StrictStr


class Abitti2StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: ktp_controller.pydantic.DateTime
    reported_at: ktp_controller.pydantic.DateTime | None
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict
    exams: typing.List[Abitti2Exam]
