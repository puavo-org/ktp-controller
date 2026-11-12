# Standard library imports
import datetime
import enum

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic
import ktp_controller.wui.schemas

__all__ = [
    "ControllerInfo",
    "Abitti2Info",
    "DiskSpaceStage",
    "calculate_disk_space_stage",
    "HostInfo",
]

_MIB = 1024**2
_GIB = 1024**3

_DISK_SPACE_CRITICAL_THRESHOLD = 100 * _MIB
_DISK_SPACE_LOW_THRESHOLD = 3 * _GIB
_DISK_SPACE_MODERATE_THRESHOLD = 10 * _GIB


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


class DiskSpaceStage(enum.StrEnum):
    PLENTY = "plenty"
    MODERATE = "moderate"
    LOW = "low"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return list(DiskSpaceStage).index(self)


def calculate_disk_space_stage(free_bytes: int) -> DiskSpaceStage:
    if free_bytes < _DISK_SPACE_CRITICAL_THRESHOLD:
        return DiskSpaceStage.CRITICAL
    if free_bytes < _DISK_SPACE_LOW_THRESHOLD:
        return DiskSpaceStage.LOW
    if free_bytes < _DISK_SPACE_MODERATE_THRESHOLD:
        return DiskSpaceStage.MODERATE
    return DiskSpaceStage.PLENTY


_DISK_SPACE_STAGE_SEVERITY: dict[
    DiskSpaceStage, ktp_controller.wui.schemas.Severity | None
] = {
    DiskSpaceStage.PLENTY: None,
    DiskSpaceStage.MODERATE: None,
    DiskSpaceStage.LOW: ktp_controller.wui.schemas.Severity.WARNING,
    DiskSpaceStage.CRITICAL: ktp_controller.wui.schemas.Severity.ERROR,
}

# Below this, the host just (re)booted. Above this, it's overdue for a
# reboot/update.
_UPTIME_JUST_BOOTED_THRESHOLD = datetime.timedelta(minutes=1)
_UPTIME_STALE_THRESHOLD = datetime.timedelta(days=60)


class HostInfo(ktp_controller.pydantic.BaseModel):
    hostname: pydantic.StrictStr | None = None
    puavo_os_image_release: pydantic.StrictStr | None
    puavo_os_image_name: pydantic.StrictStr | None
    free_disk_space_stage: DiskSpaceStage | None = None
    started_at: ktp_controller.pydantic.DateTime | None = None
    # The uptime the above started_at was computed from, kept
    # alongside it so severity can be judged against the exact
    # reported value instead of re-deriving it from started_at via a
    # second, slightly later, wall-clock read.
    uptime: pydantic.NonNegativeFloat | None = None

    @property
    def _disk_space_severity(self) -> ktp_controller.wui.schemas.Severity | None:
        if self.free_disk_space_stage is None:
            return ktp_controller.wui.schemas.Severity.ERROR
        return _DISK_SPACE_STAGE_SEVERITY[self.free_disk_space_stage]

    @property
    def _uptime_severity(self) -> ktp_controller.wui.schemas.Severity | None:
        if self.uptime is None:
            return None
        uptime = datetime.timedelta(seconds=self.uptime)
        if uptime < _UPTIME_JUST_BOOTED_THRESHOLD or uptime > _UPTIME_STALE_THRESHOLD:
            return ktp_controller.wui.schemas.Severity.WARNING
        return None

    @property
    def severity(self) -> ktp_controller.wui.schemas.Severity | None:
        return ktp_controller.wui.schemas.highest_severity(
            [self._disk_space_severity, self._uptime_severity]
        )
