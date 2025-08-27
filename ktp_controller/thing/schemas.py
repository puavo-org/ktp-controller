# Standard library imports

# Third-party imports
import pydantic
import pydantic.types

__all__ = [
    "UpsertThingRequest",
    "Thing",
]


class UpsertThingRequest(pydantic.BaseModel):
    name: pydantic.types.StrictStr
    size: pydantic.types.StrictInt


class Thing(pydantic.BaseModel):
    name: pydantic.types.StrictStr
    size: pydantic.types.StrictInt
