# Standard library imports
import enum
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic


class Abitti2MessageType(str, enum.Enum):
    EXAMS = "exams"
    SECURITY_CODE = "security-code"
    SERVERS = "servers"
    STATS = "stats"

    def __str__(self) -> str:
        return self.value


class _Abitti2BaseModel(ktp_controller.pydantic.BaseModel):
    model_config = {
        # Abitti2 objects have several fields, but we are interested
        # only some of them. But for robustness, let's allow Abitti2
        # to add and remove various fields as it likes, as long as the
        # fields we are interested are as defined in these models.
        "extra": "ignore",
    }


class Abitti2StatsMessageDataExamStatus(_Abitti2BaseModel):
    hasStarted: pydantic.StrictBool
    startTime: pydantic.AwareDatetime


class Abitti2StatsMessageDataStudent(_Abitti2BaseModel):
    studentUuid: pydantic.UUID4
    sessionUuid: pydantic.UUID4
    studentStatus: pydantic.StrictStr


class Abitti2StatsMessageData(_Abitti2BaseModel):
    students: typing.List[Abitti2StatsMessageDataStudent]
    answerPaperCount: ktp_controller.pydantic.StrictNonNegativeInt
    examStatus: Abitti2StatsMessageDataExamStatus


class Abitti2StatsMessage(_Abitti2BaseModel):
    type: typing.Literal[Abitti2MessageType.STATS] = Abitti2MessageType.STATS
    data: Abitti2StatsMessageData


class Abitti2ExamsMessage(_Abitti2BaseModel):
    examUuid: pydantic.UUID4
    examTitle: pydantic.StrictStr
    hasStarted: pydantic.StrictBool
    startTime: pydantic.AwareDatetime
