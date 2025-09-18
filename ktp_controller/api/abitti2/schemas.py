# Standard library imports
import typing

# Third-party imports
import pydantic


__all__ = [
    "PostStatusRequest",
    "PostStatusResponse",
]


class PostStatusRequest(pydantic.BaseModel):
    data: typing.Dict


class PostStatusResponse(pydantic.BaseModel):
    ok: bool
