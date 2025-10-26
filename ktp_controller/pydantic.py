import json
import typing

import pydantic

StrictPositiveInt = typing.Annotated[int, pydantic.Field(strict=True, ge=1)]
StrictSHA256String = typing.Annotated[
    str, pydantic.Field(strict=True, pattern=r"[a-f0-9]{64}")
]


class BaseModel(pydantic.BaseModel):
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "validate_default": True,
        "validate_return": True,
    }


def json_serializable(m: pydantic.BaseModel):
    return json.loads(m).model_dump_json()
