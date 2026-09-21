# Standard library imports
import asyncio
import collections.abc
import contextlib
import logging
import logging.config
import os.path
import urllib.parse

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.staticfiles
import uvicorn

# Internal imports
import ktp_controller.wui.auth
import ktp_controller.wui.auth_routes
import ktp_controller.wui.invigilator.routes
import ktp_controller.wui.middleware
import ktp_controller.wui.utils
from ktp_controller import SETTINGS

__all__ = [
    "APP",
    "run",
]


_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncIterator[None]:
    _LOGGER.info("Starting KTP Controller WUI...")

    status_report_listener_task = asyncio.create_task(
        ktp_controller.wui.utils.raw_abitti2_stats_message_listener(
            app.state.invigilator_ws_registry
        )
    )

    _LOGGER.info("Started KTP Controller WUI.")
    yield
    _LOGGER.info("Stopping KTP Controller WUI...")

    status_report_listener_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await status_report_listener_task

    _LOGGER.info("Stopped KTP Controller WUI.")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.state.invigilator_ws_registry = ktp_controller.wui.utils.BrowserSocketRegistry()
APP.add_middleware(ktp_controller.wui.middleware.OriginCheckMiddleware)
APP.add_middleware(ktp_controller.wui.middleware.SecurityHeadersMiddleware)
APP.include_router(ktp_controller.wui.invigilator.routes.router, prefix="/invigilator")
APP.include_router(ktp_controller.wui.auth_routes.router)
APP.mount(
    "/invigilator/static",
    fastapi.staticfiles.StaticFiles(
        directory=os.path.join(
            os.path.dirname(ktp_controller.wui.invigilator.routes.__file__), "static"
        )
    ),
    name="invigilator-static",
)


@APP.exception_handler(ktp_controller.wui.auth.NotAuthenticatedError)
async def _handle_not_authenticated(
    request: fastapi.Request,
    exc: ktp_controller.wui.auth.NotAuthenticatedError,
) -> fastapi.responses.RedirectResponse:
    next_qs = urllib.parse.urlencode({"next": request.url.path})
    return fastapi.responses.RedirectResponse(
        url=f"/login?{next_qs}", status_code=fastapi.status.HTTP_303_SEE_OTHER
    )


def run() -> int:
    uvicorn.run(
        "ktp_controller.wui.main:APP",
        host=SETTINGS.wui_host,
        port=SETTINGS.wui_port,
        reload=False,
    )

    return 0
