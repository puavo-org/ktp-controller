# Standard library imports
import collections.abc
import contextlib
import logging
import logging.config

# Third-party imports
import fastapi
import uvicorn

# Internal imports
import ktp_controller.wui.invigilator.routes
from ktp_controller import SETTINGS

__all__ = [
    "APP",
    "run",
]


_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncIterator[None]:
    _LOGGER.info("Starting KTP Controller WUI...")

    _LOGGER.info("Started KTP Controller WUI.")
    yield
    _LOGGER.info("Stopping KTP Controller WUI...")

    _LOGGER.info("Stopped KTP Controller WUI.")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.include_router(ktp_controller.wui.invigilator.routes.router, prefix="/invigilator")


def run() -> int:
    uvicorn.run(
        "ktp_controller.wui.main:APP",
        host=SETTINGS.wui_host,
        port=SETTINGS.wui_port,
        reload=False,
    )

    return 0
