# Standard library imports
import contextlib
import logging
import os.path

# Third-party imports
import fastapi  # type: ignore

# Internal imports
import ktp_controller.database
import ktp_controller.thing.routes
from ktp_controller.settings import SETTINGS

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(message)s",
    force=True,
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI):  # pylint: disable=unused-argument
    _LOGGER.info("Starting with following settings: %s", SETTINGS)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    database_url = f"sqlite:///{os.path.join(base_dir, 'ktp_controller.sqlite')}"
    ktp_controller.database.initialize(database_url)

    ## Alembic creates the database, this should not be needed. It's
    ## a critical error if the database does not exist when the app is
    ## started.
    # models.Base.metadata.create_all(bind=database._ENGINE)

    yield

    _LOGGER.info("Stopping...")


APP = fastapi.FastAPI(lifespan=_lifespan)
APP.include_router(ktp_controller.thing.routes.router, prefix="/api/v1/thing")
