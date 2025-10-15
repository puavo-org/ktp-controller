# Third-party imports
import sqlalchemy
import sqlalchemy.orm

__all__ = [
    "Base",
]


Base = sqlalchemy.orm.declarative_base()
