# Standard library imports
import collections.abc
import contextlib
import logging
import logging.config

# Third-party imports
import fastapi
import uvicorn

# Internal imports
import ktp_controller.api.database
import ktp_controller.api.exam.routes
import ktp_controller.api.system.routes
import ktp_controller.api.utils
from ktp_controller import SETTINGS

__all__ = [
    # Constants:
    "APP",
    # Interface:
    "run",
]


# Constants:


_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncIterator[None]:
    _LOGGER.info("Starting KTP Controller API...")

    database_url = f"sqlite:///{SETTINGS.db_path}"
    ktp_controller.api.database.initialize(database_url)

    ## Alembic creates the database, this should not be needed. It's
    ## a critical error if the database does not exist when the app is
    ## started.
    # models.Base.metadata.create_all(bind=database._ENGINE)

    await app.state.pubsub_broadcaster.start()

    _LOGGER.info("Started KTP Controller API.")
    yield
    _LOGGER.info("Stopping KTP Controller API...")

    await app.state.pubsub_broadcaster.stop()

    _LOGGER.info("Stopped KTP Controller API.")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.state.pubsub_broadcaster = ktp_controller.api.utils.PubSubBroadcaster()
APP.include_router(ktp_controller.api.exam.routes.router, prefix="/api/v1/exam")
APP.include_router(ktp_controller.api.system.routes.router, prefix="/api/v1/system")


def run() -> int:
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

    return 0
