# Standard library imports
import dataclasses
import datetime
import logging
import os.path
import typing

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.api.client
import ktp_controller.utils
import ktp_controller.wui.auth
import ktp_controller.wui.i18n
import ktp_controller.wui.schemas
import ktp_controller.wui.students
from ktp_controller import DATADIR, WORKDIR

# Relative imports
from . import schemas

__all__ = [
    "router",
    "get_nav_severity",
]

_LOGGER = logging.getLogger(__name__)

_CERT_EXPIRY_WARNING_THRESHOLD = datetime.timedelta(days=16)

router = fastapi.APIRouter(tags=["htmx"])
_thisdir = os.path.dirname(__file__)
_templates = fastapi.templating.Jinja2Templates(
    directory=[
        os.path.join(_thisdir, "templates"),
        os.path.join(os.path.dirname(_thisdir), "templates"),
    ],
    context_processors=[ktp_controller.wui.i18n.template_context_processor],
)
_templates.env.autoescape = True
_templates.env.add_extension("jinja2.ext.i18n")
_templates.env.install_null_translations(newstyle=True)  # type: ignore[attr-defined]
_templates.env.filters["localize_datetime"] = ktp_controller.wui.i18n.localize_datetime
_templates.env.filters["localize_date"] = ktp_controller.wui.i18n.localize_date


@dataclasses.dataclass(frozen=True)
class _Card:
    key: str
    # None means every session that can reach the landing page at all
    # (i.e. holds wui.landing.view) sees this card. A future
    # role-specific card can require an additional permission here,
    # granted to only the relevant role via its own migration.
    required_permission: str | None


# Cards shown on the landing page, in display order.
_CARDS = (
    _Card(key="controller_info", required_permission=None),
    _Card(key="abitti2_info", required_permission=None),
    _Card(key="host_info", required_permission=None),
)


def _visible_card_keys(session: ktp_controller.wui.auth.Session) -> list[str]:
    return [
        card.key
        for card in _CARDS
        if card.required_permission is None
        or card.required_permission in session.permissions
    ]


def _get_controller_info(
    report: dict[str, typing.Any] | None,
) -> schemas.ControllerInfo | None:
    if report is None:
        return None
    ktp_controller_report = report["ktp_controller"]
    return schemas.ControllerInfo(
        version=ktp_controller_report["version"],
        started_at=ktp_controller_report["started_at"],
        is_auto_control_enabled=ktp_controller_report["is_auto_control_enabled"],
    )


def _format_cert_expiry_countdown(remaining: datetime.timedelta, locale: str) -> str:
    _ = ktp_controller.wui.i18n.get_gettext(locale)
    ngettext = ktp_controller.wui.i18n.get_ngettext(locale)
    if remaining <= datetime.timedelta(0):
        return _("Expired")
    if remaining.days >= 1:
        return ngettext("%(num)s day left", "%(num)s days left", remaining.days) % {
            "num": remaining.days
        }
    hours = remaining.seconds // 3600
    return ngettext("%(num)s hour left", "%(num)s hours left", hours) % {"num": hours}


def _get_abitti2_info(
    report: dict[str, typing.Any] | None,
    locale: str,
) -> schemas.Abitti2Info | None:
    if report is None:
        return None
    cert = report["abitti2"].get("cert")
    abitti2_info = schemas.Abitti2Info(
        version=report["abitti2"]["version"],
        server_name=ktp_controller.abitti2.utils.parse_server_name(
            report["abitti2"]["domain"]
        ),
        cert_expires_at=cert["expires_at"] if cert else None,
    )
    # cert_expires_at above is validated/parsed into a real datetime by
    # pydantic, even though the raw report value is a JSON string.
    if abitti2_info.cert_expires_at is not None:
        remaining = abitti2_info.cert_expires_at - ktp_controller.utils.utcnow()
        abitti2_info.cert_expiring_soon = remaining < _CERT_EXPIRY_WARNING_THRESHOLD
        if abitti2_info.cert_expiring_soon:
            abitti2_info.cert_expiry_countdown_text = _format_cert_expiry_countdown(
                remaining, locale
            )
    return abitti2_info


def _get_relevant_disk_usages(
    report: dict[str, typing.Any],
) -> list[dict[str, typing.Any]]:
    disk_usage_stats = report["os"].get("stats", {}).get("disk_usage")
    if not disk_usage_stats:
        return []
    return [
        entry
        for entry in disk_usage_stats
        if entry.get("dirpath") in {DATADIR, WORKDIR}
    ]


def _get_host_info(
    report: dict[str, typing.Any] | None,
) -> schemas.HostInfo | None:
    if report is None:
        return None
    disk_usages = _get_relevant_disk_usages(report)
    if disk_usages:
        free_bytes = [du["free"] for du in disk_usages]
        disk_space_stages = [
            schemas.calculate_disk_space_stage(fb) for fb in free_bytes
        ]
        most_critical_disk_space_stage = sorted(
            disk_space_stages, key=lambda dss: dss.rank
        )[-1]
    else:
        most_critical_disk_space_stage = None
    return schemas.HostInfo(
        puavo_os_image_release=report["os"]["puavo_os_image_release"],
        puavo_os_image_name=report["os"]["puavo_os_image_name"],
        free_disk_space_stage=most_critical_disk_space_stage,
    )


def _get_disk_space_stage_labels(
    _: typing.Callable[[str], str],
) -> dict[schemas.DiskSpaceStage, str]:
    # Insertion order is the rendering order.
    return {
        schemas.DiskSpaceStage.PLENTY: _("Plenty"),
        schemas.DiskSpaceStage.MODERATE: _("Moderate"),
        schemas.DiskSpaceStage.LOW: _("Low"),
        schemas.DiskSpaceStage.CRITICAL: _("Critical"),
    }


def get_nav_severity(
    report: dict[str, typing.Any] | None, locale: str
) -> ktp_controller.wui.schemas.Severity | None:
    return ktp_controller.wui.schemas.highest_severity(
        info.severity
        for info in (
            _get_controller_info(report),
            _get_abitti2_info(report, locale),
            _get_host_info(report),
        )
        if info is not None
    )


@router.get("/", response_class=fastapi.responses.HTMLResponse)
@ktp_controller.wui.auth.require_permission("wui.landing.view")
async def _get_landing(
    request: fastapi.Request,
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.HTMLResponse:
    report = await ktp_controller.api.client.get_last_status_report()

    request.state.locale = session.locale
    _ = ktp_controller.wui.i18n.get_gettext(session.locale)

    student_list_items = await ktp_controller.wui.students.get_student_list_items()
    student_state_counts = ktp_controller.wui.students.count_student_states(
        student_list_items
    )
    state_labels = ktp_controller.wui.students.get_student_state_labels(_)
    disk_space_stage_labels = _get_disk_space_stage_labels(_)

    context = {
        "user": session.username,
        "visible_card_keys": _visible_card_keys(session),
        "controller_info": _get_controller_info(report),
        "abitti2_info": _get_abitti2_info(report, session.locale),
        "host_info": _get_host_info(report),
        "nav_severity": get_nav_severity(report, session.locale),
        "current_path": request.url.path,
        # Hardcoded until a "wui.actions.toggle-auto-control" permission
        # and its action endpoint exist.
        "can_toggle_auto_control": False,
        "student_state_counts": student_state_counts,
        "state_labels": state_labels,
        "disk_space_stage_labels": disk_space_stage_labels,
    }

    # If the request comes from htmx, return only the pills partial
    if request.headers.get("HX-Request"):
        return _templates.TemplateResponse(
            request, name="partials/nav_student_state_counts.html.j2", context=context
        )

    # Otherwise return the full page
    return _templates.TemplateResponse(
        request, name="landing_index.html.j2", context=context
    )
