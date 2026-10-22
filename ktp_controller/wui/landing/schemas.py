# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

__all__ = [
    "GeneralInfo",
    "Abitti2Info",
]


class GeneralInfo(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime
    is_auto_control_enabled: pydantic.StrictBool


class Abitti2Info(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr | None
