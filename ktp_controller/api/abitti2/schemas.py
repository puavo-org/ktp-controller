# Standard library imports
import datetime
import typing

# Third-party imports
import pydantic

import ktp_controller.pydantic

__all__ = [
    "StatusReport",
]


class StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: datetime.datetime
    reported_at: datetime.datetime | None
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict
