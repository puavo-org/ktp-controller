# Standard library imports
import collections.abc

# Third-party imports
import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm

__all__ = [
    # Utils:
    "get_db",
    "initialize",
]


# Constants:


_ENGINE: sqlalchemy.engine.Engine | None = None
_SESSION_MAKER: sqlalchemy.orm.sessionmaker[sqlalchemy.orm.Session] | None = None


# Utils:


def initialize(database_url: str) -> None:
    global _ENGINE
    global _SESSION_MAKER

    if (_ENGINE, _SESSION_MAKER) != (None, None):
        raise RuntimeError("already initialized")

    _ENGINE = sqlalchemy.create_engine(
        database_url,
        connect_args={
            ## Allow multiple threads to use the same sqlite
            ## database. This is safe because requests do not share db
            ## sesssions.
            "check_same_thread": False,
        },
    )

    _SESSION_MAKER = sqlalchemy.orm.sessionmaker(
        autocommit=False, autoflush=False, bind=_ENGINE
    )


def get_db() -> collections.abc.Iterator[sqlalchemy.orm.Session]:
    """Return SQL Alchemy database session"""
    assert _SESSION_MAKER is not None
    db = _SESSION_MAKER()
    try:
        yield db
    finally:
        db.close()
