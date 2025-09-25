# Standard library imports
import typing

# Third-party imports
import pydantic


__all__ = [
    "PushAbitti2StatusRequest",
    "PushAbitti2StatusResponse",
]


class PushAbitti2StatusRequest(pydantic.BaseModel):
    status: typing.Dict


class PushAbitti2StatusResponse(pydantic.BaseModel):
    ok: bool
