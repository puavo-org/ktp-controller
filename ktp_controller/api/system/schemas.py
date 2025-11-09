# Standard library imports
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
    received_at: ktp_controller.pydantic.DateTime
    reported_at: ktp_controller.pydantic.DateTime | None
    monitoring_passphrase: pydantic.StrictStr
    server_version: pydantic.StrictStr
    status: typing.Dict
