# Standard library imports
import contextlib
import logging
import logging.config
import os.path

# Third-party imports
import fastapi  # type: ignore
import uvicorn  # type: ignore

# Internal imports
import ktp_controller.api.database
import ktp_controller.api.status.routes
import ktp_controller.api.abitti2.routes
from ktp_controller.settings import SETTINGS

_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI):  # pylint: disable=unused-argument
    _LOGGER.info("Starting...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    database_url = f"sqlite:///{os.path.join(base_dir, 'ktp_controller.sqlite')}"
    ktp_controller.api.database.initialize(database_url)

    ## Alembic creates the database, this should not be needed. It's
    ## a critical error if the database does not exist when the app is
    ## started.
    # models.Base.metadata.create_all(bind=database._ENGINE)

    yield

    _LOGGER.info("Stopping...")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.include_router(ktp_controller.api.status.routes.router, prefix="/api/v1/status")
APP.include_router(ktp_controller.api.abitti2.routes.router, prefix="/api/v1/status")


def run():
    uvicorn.run(
        "ktp_controller.api.main:APP",
        host=SETTINGS.api_host,
        port=SETTINGS.api_port,
        reload=False,
        #        log_config={
        #            "version": 1,
        #            "level": "DEBUG",
        #            "format": ktp_controller.DEFAULT_LOGGING_FORMAT,
        #        },
    )
