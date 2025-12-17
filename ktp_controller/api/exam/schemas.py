# Standard library imports
import enum
import typing
from typing_extensions import Self

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
    "SetCurrentExamPackageStateData",
]


# Types:


class ExamFileInfo(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    name: pydantic.StrictStr
    size: ktp_controller.pydantic.StrictPositiveInt
    sha256: ktp_controller.pydantic.StrictSHA256String
    decrypt_code: pydantic.StrictStr
    modified_at: ktp_controller.pydantic.DateTime


class ScheduledExam(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    exam_title: pydantic.StrictStr
    start_time: ktp_controller.pydantic.DateTime
    end_time: ktp_controller.pydantic.DateTime
    exam_file_info: ExamFileInfo
    modified_at: ktp_controller.pydantic.DateTime

    @pydantic.model_validator(mode="after")
    def check_times(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("start_time >= end_time", self.start_time, self.end_time)
        return self


class ScheduledExamPackageState(str, enum.Enum):
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        return self.value


class ScheduledExamPackage(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    start_time: ktp_controller.pydantic.DateTime
    end_time: ktp_controller.pydantic.DateTime
    lock_time: ktp_controller.pydantic.DateTime | None
    locked: pydantic.StrictBool
    scheduled_exam_external_ids: typing.List[pydantic.StrictStr]
    state: ScheduledExamPackageState | None
    state_changed_at: ktp_controller.pydantic.DateTime | None

    @pydantic.model_validator(mode="after")
    def check_times(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("start_time >= end_time", self.start_time, self.end_time)
        return self


class ExamInfo(ktp_controller.pydantic.BaseModel):
    scheduled_exams: typing.List[ScheduledExam]
    scheduled_exam_packages: typing.List[ScheduledExamPackage]
    request_id: pydantic.StrictStr
    raw_data: typing.Dict[str, typing.Any]


class GetScheduledExamData(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr


class SetCurrentExamPackageStateData(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
    state: ScheduledExamPackageState


class GetScheduledExamPackageData(ktp_controller.pydantic.BaseModel):
    external_id: pydantic.StrictStr
