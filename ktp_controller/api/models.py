from __future__ import annotations

# Standard library imports
import datetime
import typing

# Third-party imports
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.orm import Mapped, mapped_column

__all__ = [
    "Base",
    "ExamFileInfo",
    "ExamInfo",
    "ScheduledExam",
    "ScheduledExamPackage",
    "Abitti2StatusReport",
]


Base = sqlalchemy.orm.declarative_base()


class ExamFileInfo(Base):  # type: ignore
    __tablename__ = "exam_file_info"

    dbid: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    dbrow_created_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    external_id: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
        index=True,
        unique=True,
    )
    name: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
    )
    size: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
    )
    sha256: Mapped[str] = mapped_column(
        sqlalchemy.String(64),
        nullable=False,
    )
    decrypt_code: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    scheduled_exam: Mapped[ScheduledExam | None] = sqlalchemy.orm.relationship(
        back_populates="exam_file_info"
    )


class ScheduledExam(Base):  # type: ignore
    __tablename__ = "scheduled_exam"

    dbid: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    dbrow_created_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True,
    )

    exam_file_info_dbid: Mapped[int] = mapped_column(
        sqlalchemy.ForeignKey("exam_file_info.dbid"),
        default=None,
        nullable=False,
    )
    scheduled_exam_package_dbid: Mapped[int | None] = mapped_column(
        sqlalchemy.ForeignKey("scheduled_exam_package.dbid"),
        default=None,
        nullable=True,
    )

    external_id: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
        index=True,
        unique=True,
    )
    exam_title: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
    )
    start_time: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    end_time: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    scheduled_exam_package: Mapped[
        ScheduledExamPackage | None
    ] = sqlalchemy.orm.relationship(back_populates="scheduled_exams")
    exam_file_info: Mapped[ExamFileInfo] = sqlalchemy.orm.relationship(
        back_populates="scheduled_exam"
    )


class ScheduledExamPackage(Base):  # type: ignore
    __tablename__ = "scheduled_exam_package"

    dbid: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    dbrow_created_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True,
    )

    external_id: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
        index=True,
        unique=True,
    )
    start_time: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    end_time: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        nullable=False,
    )
    lock_time: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        nullable=True,
    )
    locked: Mapped[bool] = mapped_column(
        sqlalchemy.Boolean,
        nullable=False,
    )

    # Unique nullable ensure only one row can have this column set,
    # which means that at most one scheduled exam package can be
    # "current" at any given time.
    current: Mapped[bool] = mapped_column(
        sqlalchemy.Boolean,
        nullable=True,
        unique=True,
    )

    state: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=True,
    )

    scheduled_exams: Mapped[typing.List[ScheduledExam]] = sqlalchemy.orm.relationship(
        back_populates="scheduled_exam_package"
    )


class ExamInfo(Base):  # type: ignore
    __tablename__ = "exam_info"

    dbid: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    dbrow_created_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True,
    )

    request_id: Mapped[str] = mapped_column(
        sqlalchemy.String,
        nullable=False,
        index=True,
        unique=True,
    )

    raw_data: Mapped[sqlalchemy.JSON] = mapped_column(
        sqlalchemy.JSON,
        nullable=False,
    )


class Abitti2StatusReport(Base):  # type: ignore
    __tablename__ = "abitti2_status_report"

    dbid: Mapped[int] = mapped_column(
        sqlalchemy.Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    dbrow_created_at: Mapped[datetime.datetime] = mapped_column(
        sqlalchemy.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True,
    )

    raw_data: Mapped[sqlalchemy.JSON] = mapped_column(
        sqlalchemy.JSON,
        nullable=False,
    )
