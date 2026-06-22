# Standard library imports
import typing

# Third-party imports

# Internal imports
import ktp_controller.examomatic.schemas
import ktp_controller.pydantic

# Relative imports


__all__ = [
    "StatusReport",
    "Echo",
]


class StatusReport(ktp_controller.examomatic.schemas.StatusReport):
    reported_at: ktp_controller.pydantic.DateTime | None


class _EchoGETRequest(ktp_controller.pydantic.BaseModel):
    method: typing.Literal["GET"] = "GET"
    received_at: ktp_controller.pydantic.DateTime
    headers: dict[str, str]


class Echo(ktp_controller.pydantic.BaseModel):
    request: _EchoGETRequest
