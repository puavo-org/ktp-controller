# Standard library imports
import contextlib
import logging
import logging.config

# Third-party imports
import fastapi  # type: ignore
import uvicorn  # type: ignore

# Internal imports
import ktp_controller.api.database
import ktp_controller.api.exam.routes
import ktp_controller.api.system.routes
from ktp_controller.settings import SETTINGS


__all__ = [
    # Constants:
    "APP",
    # Interface:
    "run",
]


# Constants:


_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI):  # pylint: disable=unused-argument
    _LOGGER.info("Starting...")
    database_url = f"sqlite:///{SETTINGS.db_path}"
    ktp_controller.api.database.initialize(database_url)

    ## Alembic creates the database, this should not be needed. It's
    ## a critical error if the database does not exist when the app is
    ## started.
    # models.Base.metadata.create_all(bind=database._ENGINE)

    yield

    _LOGGER.info("Stopping...")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.include_router(ktp_controller.api.exam.routes.router, prefix="/api/v1/exam")
APP.include_router(ktp_controller.api.system.routes.router, prefix="/api/v1/system")


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
