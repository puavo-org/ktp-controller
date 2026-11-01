# Standard library imports
import logging
import os.path
import urllib.parse

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.api.client
import ktp_controller.wui.auth
import ktp_controller.wui.i18n
import ktp_controller.wui.landing.routes

__all__ = [
    "router",
]

_LOGGER = logging.getLogger(__name__)

router = fastapi.APIRouter(tags=["htmx"])
_thisdir = os.path.dirname(__file__)
_templates = fastapi.templating.Jinja2Templates(
    directory=os.path.join(os.path.dirname(_thisdir), "templates"),
    context_processors=[ktp_controller.wui.i18n.template_context_processor],
)
_templates.env.autoescape = True
_templates.env.add_extension("jinja2.ext.i18n")
_templates.env.install_null_translations(newstyle=True)  # type: ignore[attr-defined]


def _has_live_update_permission(session: ktp_controller.wui.auth.Session) -> bool:
    return (
        "wui.invigilator.view" in session.permissions
        or "wui.landing.view" in session.permissions
    )


@router.get("/nav_status", response_class=fastapi.responses.HTMLResponse)
async def _get_nav_status(
    request: fastapi.Request,
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.HTMLResponse:
    if not _has_live_update_permission(session):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN, detail="Forbidden"
        )

    report = await ktp_controller.api.client.get_last_status_report()

    request.state.locale = session.locale

    # This endpoint's own self-refresh request always targets this same
    # path ("/nav_status"), so request.url.path can't tell which page the
    # browser is actually showing. HX-Current-URL is sent automatically by
    # htmx on every triggered request and carries the browser's real
    # location instead.
    current_url = request.headers.get("HX-Current-URL")
    current_path = (
        urllib.parse.urlparse(current_url).path
        if current_url is not None
        else request.url.path
    )

    context = {
        "current_path": current_path,
        "nav_severity": ktp_controller.wui.landing.routes.get_nav_severity(
            report, session.locale
        ),
    }

    return _templates.TemplateResponse(
        request, name="partials/nav_exam_server_link.html.j2", context=context
    )
