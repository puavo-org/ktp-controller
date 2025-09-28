# Standard library imports
import datetime
import enum
import typing

# Third-party imports
import pydantic

__all__ = [
    "ExamFileInfo",
    "ExamInfo",
    "GetScheduledExamData",
    "ScheduledExam",
    "ScheduledExamPackage",
    "ScheduledExamPackageState",
    "SetCurrentScheduledExamPackageStateData",
]


StrictPositiveInt = typing.Annotated[int, pydantic.Field(strict=True, ge=1)]
StrictSHA256String = typing.Annotated[
    str, pydantic.Field(strict=True, pattern=r"[a-f0-9]{64}")
]


class _BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")


class ExamFileInfo(_BaseModel):
    external_id: pydantic.StrictStr
    name: pydantic.StrictStr
    size: StrictPositiveInt
    sha256: StrictSHA256String
    decrypt_code: pydantic.StrictStr
    modified_at: datetime.datetime


class ScheduledExam(_BaseModel):
    external_id: pydantic.StrictStr
    exam_title: pydantic.StrictStr
    start_time: datetime.datetime
    end_time: datetime.datetime
    exam_file_info: ExamFileInfo
    modified_at: datetime.datetime


class ScheduledExamPackageState(str, enum.Enum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        return self.value


class ScheduledExamPackage(_BaseModel):
    external_id: pydantic.StrictStr
    start_time: datetime.datetime
    end_time: datetime.datetime
    lock_time: datetime.datetime | None
    locked: pydantic.StrictBool
    scheduled_exam_external_ids: typing.List[pydantic.StrictStr]
    state: ScheduledExamPackageState | None


class ExamInfo(_BaseModel):
    scheduled_exams: typing.List[ScheduledExam]
    scheduled_exam_packages: typing.List[ScheduledExamPackage]
    request_id: pydantic.StrictStr
    raw_data: typing.Dict[str, typing.Any]


class GetScheduledExamData(_BaseModel):
    external_id: pydantic.StrictStr


class SetCurrentScheduledExamPackageStateData(_BaseModel):
    external_id: pydantic.StrictStr
    state: ScheduledExamPackageState
