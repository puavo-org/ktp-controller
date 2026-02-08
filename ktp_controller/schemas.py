# Standard library imports
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic


__all__ = [
    "FileStat",
    "FileStats",
    "StudentAccessCode",
]


class StudentAccessCode(ktp_controller.pydantic.BaseModel):
    key_code: pydantic.StrictStr
    verification_code: pydantic.StrictStr


class FileStat(ktp_controller.pydantic.BaseModel):
    path: pydantic.StrictStr
    size: ktp_controller.pydantic.StrictNonNegativeInt
    modified_at: ktp_controller.pydantic.DateTime


class FileStats(ktp_controller.pydantic.BaseModel):
    exams: typing.List[FileStat]
    exam_packages: typing.List[FileStat]
    answers: typing.List[FileStat]
