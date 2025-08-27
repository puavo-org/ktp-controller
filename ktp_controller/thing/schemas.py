# Standard library imports

# Third-party imports
import pydantic


__all__ = [
    "UpsertThingRequest",
    "Thing",
]


class UpsertThingRequest(pydantic.BaseModel):
    name: pydantic.StrictStr
    size: pydantic.StrictInt


class Thing(pydantic.BaseModel):
    name: pydantic.StrictStr
    size: pydantic.StrictInt
