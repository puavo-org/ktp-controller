# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic


__all__ = [
    "StudentAccessCode",
]


class StudentAccessCode(ktp_controller.pydantic.BaseModel):
    key_code: pydantic.StrictStr
    verification_code: pydantic.StrictStr
