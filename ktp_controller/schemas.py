# Standard library imports
import typing

# Third-party imports
import pydantic
from pydantic import Field

# Internal imports
import ktp_controller.pydantic


__all__ = [
    "FileStat",
    "FileStats",
    "StudentAccessCode",
]


class StudentAccessCode(ktp_controller.pydantic.BaseModel):
    key_code: pydantic.StrictStr = Field(examples=["1234"])
    verification_code: pydantic.StrictStr = Field(examples=["xx"])


class FileStat(ktp_controller.pydantic.BaseModel):
    path: pydantic.StrictStr = Field(
        examples=[
            "/home/puavo-ers/.local/share/ktp-controller/exam-files/90d99c0a-87b2-49b3-b791-3090550f6345/exam-file.mex"
        ]
    )
    size: ktp_controller.pydantic.StrictNonNegativeInt = Field(examples=[15948894])
    modified_at: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-03-26T20:02:06.343+0000"]
    )


class FileStats(ktp_controller.pydantic.BaseModel):
    exams: typing.List[FileStat]
    exam_packages: typing.List[FileStat]
    answers: typing.List[FileStat]
