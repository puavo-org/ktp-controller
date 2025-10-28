# Standard library imports
import datetime
import enum
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

# Relative imports

__all__ = [
    # Types:
    "ExamFileInfo",
    "ExamInfo",
    "GetScheduledExamData",
    "ScheduledExam",
    "ScheduledExamPackage",
    "ScheduledExamPackageState",
    "SetCurrentScheduledExamPackageStateData",
]


# Types:


class ExamFileInfo(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    name: pydantic.StrictStr
    size: ktp_controller.pydantic.StrictPositiveInt
    sha256: ktp_controller.pydantic.StrictSHA256String
    decrypt_code: pydantic.StrictStr
    modified_at: datetime.datetime


class ScheduledExam(ktp_controller.pydantic.BaseModel):
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
    STOPPING = "stopping"
    STOPPED = "stopped"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        return self.value


class ScheduledExamPackage(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    start_time: datetime.datetime
    end_time: datetime.datetime
    lock_time: datetime.datetime | None
    locked: pydantic.StrictBool
    scheduled_exam_external_ids: typing.List[pydantic.StrictStr]
    state: ScheduledExamPackageState | None
    state_changed_at: datetime.datetime | None


class ExamInfo(ktp_controller.pydantic.BaseModel):
    scheduled_exams: typing.List[ScheduledExam]
    scheduled_exam_packages: typing.List[ScheduledExamPackage]
    request_id: pydantic.StrictStr
    raw_data: typing.Dict[str, typing.Any]


class GetScheduledExamData(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr


class SetCurrentScheduledExamPackageStateData(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    state: ScheduledExamPackageState
