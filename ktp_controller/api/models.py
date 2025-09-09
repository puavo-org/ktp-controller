# Third-party imports
import sqlalchemy
import sqlalchemy.orm

__all__ = [
    "Base",
    "Thing",
]


Base = sqlalchemy.orm.declarative_base()


class Thing(Base):  # type: ignore
    __tablename__ = "things"
    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True, index=True)
    size = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
