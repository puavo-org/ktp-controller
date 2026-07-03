# Standard library imports
import typing

import ktp_controller.pydantic

# Third-party imports
# Internal imports
import ktp_controller.schemas

# Relative imports


__all__ = [
    "Echo",
    "StatusReport",
]


class StatusReport(ktp_controller.schemas.StatusReport):
    reported_at: ktp_controller.pydantic.DateTime | None


class _EchoGETRequest(ktp_controller.pydantic.BaseModel):
    method: typing.Literal["GET"] = "GET"
    received_at: ktp_controller.pydantic.DateTime
    headers: dict[str, str]


class Echo(ktp_controller.pydantic.BaseModel):
    request: _EchoGETRequest
