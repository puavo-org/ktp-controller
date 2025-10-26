# Standard library imports
import datetime
import typing

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

# Relative imports


__all__ = [
    # Types:
    "Abitti2StatusReport",
]


# Types:


class Abitti2StatusReport(ktp_controller.pydantic.BaseModel):
    received_at: datetime.datetime
    reported_at: datetime.datetime | None
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict
