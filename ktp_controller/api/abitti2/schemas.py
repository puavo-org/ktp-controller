# Standard library imports
import datetime
import typing

# Third-party imports
import pydantic

__all__ = [
    "StatusReport",
]


class StatusReport(pydantic.BaseModel):
    received_at: datetime.datetime
    reported_at: typing.Optional[datetime.datetime]
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict
