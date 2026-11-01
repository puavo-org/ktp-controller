# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic
import ktp_controller.wui.schemas

__all__ = [
    "ControllerInfo",
    "Abitti2Info",
    "OsInfo",
]


class ControllerInfo(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr
    started_at: ktp_controller.pydantic.DateTime
    is_auto_control_enabled: pydantic.StrictBool

    @property
    def severity(self) -> ktp_controller.wui.schemas.Severity | None:
        return None


class Abitti2Info(ktp_controller.pydantic.BaseModel):
    version: pydantic.StrictStr | None
    server_name: pydantic.StrictStr | None
    cert_expires_at: ktp_controller.pydantic.DateTime | None = None
    cert_expiring_soon: pydantic.StrictBool = False
    cert_expiry_countdown_text: pydantic.StrictStr | None = None

    @property
    def severity(self) -> ktp_controller.wui.schemas.Severity | None:
        # Once a second issue-producing field is added here, switch
        # this to ktp_controller.wui.schemas.highest_severity([...]).
        if self.cert_expiring_soon:
            return ktp_controller.wui.schemas.Severity.WARNING
        return None


class OsInfo(ktp_controller.pydantic.BaseModel):
    puavo_os_image_release: pydantic.StrictStr | None
    puavo_os_image_name: pydantic.StrictStr | None

    @property
    def severity(self) -> ktp_controller.wui.schemas.Severity | None:
        return None
