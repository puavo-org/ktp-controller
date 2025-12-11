# Standard library imports
import datetime
import json
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.utils

# Relative imports


__all__ = [
    # Types:
    "StrictPositiveInt",
    "StrictSHA256String",
    "BaseModel",
    "DateTime",
    # Utils:
    "json_serializable",
]


# Types:


StrictNonNegativeInt = typing.Annotated[int, pydantic.Field(strict=True, ge=0)]
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


def _dt_to_str(dt) -> str:
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        raise RuntimeError("datetime is naive", dt)
    return ktp_controller.utils.strfdt(dt)


DateTime = typing.Annotated[
    pydantic.AwareDatetime,
    pydantic.PlainSerializer(
        _dt_to_str,
        return_type=str,
    ),
]
