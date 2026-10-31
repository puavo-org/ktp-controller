# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

__all__ = [
    "ControllerInfo",
    "Abitti2Info",
    "OsInfo",
]


class ControllerInfo(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime
    is_auto_control_enabled: pydantic.StrictBool


class Abitti2Info(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr | None
    server_name: pydantic.StrictStr | None
    cert_expires_at: ktp_controller.pydantic.DateTime | None = None
    cert_expiring_soon: pydantic.StrictBool = False
    cert_expiry_countdown_text: pydantic.StrictStr | None = None


class OsInfo(ktp_controller.pydantic.BaseModel):
    puavo_os_image_release: pydantic.StrictStr | None
    puavo_os_image_name: pydantic.StrictStr | None
