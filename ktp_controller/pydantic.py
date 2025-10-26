# Standard library imports
import json
import typing

# Third-party imports
import pydantic

# Internal imports

# Relative imports


__all__ = [
    # Types:
    "StrictPositiveInt",
    "StrictSHA256String",
    "BaseModel",
    # Utils:
    "json_serializable",
]


# Types:


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


# Utils:


def json_serializable(m: pydantic.BaseModel):
    return json.loads(m.model_dump_json())
