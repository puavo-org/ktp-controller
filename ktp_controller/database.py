# Standard library imports
import os

# Third-party imports
import sqlalchemy
import sqlalchemy.orm


__all__ = [
    "get_db",
    "initialize",
]

_ENGINE = None
_SESSION_MAKER = None


def initialize(database_url):
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


def get_db():
    """Return SQL Alchemy database session"""
    db = _SESSION_MAKER()
    try:
        yield db
    finally:
        db.close()
