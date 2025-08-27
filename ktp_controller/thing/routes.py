# Standard library imports
import logging
import typing

# Third-party imports
import fastapi  # type: ignore
import pydantic
import sqlalchemy.orm

# Internal imports
from ktp_controller.database import get_db
from ktp_controller.models import Thing
from . import schemas as thing_schemas


_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["thing"])


@router.get(
    "/",
    response_model=typing.List[thing_schemas.Thing],
    summary="Get all things",
)
def _get_all_things(
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    """
    Return all things.
    """
    db_things = db.query(Thing).all()
    return [
        thing_schemas.Thing(name=db_thing.name, size=db_thing.size)
        for db_thing in db_things
    ]


@router.get(
    "/{name}",
    response_model=thing_schemas.Thing,
    summary="Get a thing",
)
def _get_thing(
    name: pydantic.StrictStr,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    """
    Return a thing by its name.
    """
    db_thing = db.query(Thing).filter_by(name=name).one_or_none()
    if db_thing is None:
        raise fastapi.HTTPException(
            status_code=404, detail=f"Thing '{name}' does not exist"
        )

    return thing_schemas.Thing(name=db_thing.name, size=db_thing.size)


@router.post(
    "/",
    response_model=thing_schemas.Thing,
    summary="Upsert a thing",
)
def _upsert_thing(
    request: thing_schemas.UpsertThingRequest,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    """
    Upsert a thing.

    Return the whole thing.
    """
    db_thing = db.query(Thing).filter_by(name=request.name).one_or_none()
    if db_thing is None:
        db_thing = Thing(id=None, name=request.name, size=request.size)
        db.add(db_thing)
    else:
        db_thing.size = request.size

    thing = thing_schemas.Thing(name=db_thing.name, size=db_thing.size)

    db.commit()

    return thing
