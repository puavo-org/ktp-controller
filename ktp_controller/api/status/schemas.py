# Standard library imports
import typing

# Third-party imports
import pydantic


__all__ = [
    "UpdateAbitti2StatusRequest",
    "UpdateAbitti2StatusResponse",
]


class UpdateAbitti2StatusRequest(pydantic.BaseModel):
    data: typing.Dict


class UpdateAbitti2StatusResponse(pydantic.BaseModel):
    ok: bool
