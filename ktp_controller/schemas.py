# Standard library imports
import enum

# Third-party imports
import pydantic
from pydantic import Field

# Internal imports
import ktp_controller.pydantic

__all__ = [
    "CachedFile",
    "CachedFiles",
    "StudentAccessCode",
    "StudentFlag",
]


class StudentFlag(enum.StrEnum):
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    WAITING_FOR_AUTH = "waiting-for-auth"
    UNDEFINED_EXAM = "undefined-exam"


class StudentAccessCode(ktp_controller.pydantic.BaseModel):
    key_code: pydantic.StrictStr = Field(examples=["1234"])
    verification_code: pydantic.StrictStr = Field(examples=["xx"])


class CachedFile(ktp_controller.pydantic.BaseModel):
    path: pydantic.StrictStr = Field(
        examples=[
            "/home/puavo-ers/.local/share/ktp-controller/exam-files/90d99c0a-87b2-49b3-b791-3090550f6345/exam-file.mex"
        ]
    )
    size: ktp_controller.pydantic.StrictNonNegativeInt = Field(examples=[15948894])
    modified_at: ktp_controller.pydantic.DateTime = Field(
        examples=["2026-03-26T20:02:06.343+0000"]
    )


class CachedFiles(ktp_controller.pydantic.BaseModel):
    exams: list[CachedFile]
    exam_packages: list[CachedFile]
    answers: list[CachedFile]
