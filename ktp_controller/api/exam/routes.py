# Standard library imports
import datetime
import logging


# Third-party imports
import fastapi
import fastapi.exceptions
import sqlalchemy.orm
import sqlalchemy.sql

# Internal imports
import ktp_controller.utils
from ktp_controller.api import models
from ktp_controller.api.database import get_db

# Relative imports
from . import schemas


_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["exam"])


async def _save_exam_file_info(
    exam_file_info: schemas.ExamFileInfo,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
) -> models.ExamFileInfo:
    db_exam_file_info = (
        db.query(models.ExamFileInfo)
        .filter_by(external_id=exam_file_info.external_id)
        .one_or_none()
    )
    if db_exam_file_info is None:
        db_exam_file_info = models.ExamFileInfo(
            dbid=None,
            external_id=exam_file_info.external_id,
            name=exam_file_info.name,
            size=exam_file_info.size,
            sha256=exam_file_info.sha256,
            decrypt_code=exam_file_info.decrypt_code,
            modified_at=exam_file_info.modified_at,
        )
        db.add(db_exam_file_info)
        db.flush()
        db.refresh(db_exam_file_info)
    else:
        db_exam_file_info.name = exam_file_info.name
        db_exam_file_info.size = exam_file_info.size
        db_exam_file_info.sha256 = exam_file_info.sha256
        db_exam_file_info.decrypt_code = exam_file_info.decrypt_code
        db_exam_file_info.modified_at = exam_file_info.modified_at

    return db_exam_file_info


async def _save_scheduled_exam(
    scheduled_exam: schemas.ScheduledExam,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
) -> models.ScheduledExam:
    db_exam_file_info = await _save_exam_file_info(scheduled_exam.exam_file_info, db)

    db_scheduled_exam = (
        db.query(models.ScheduledExam)
        .filter_by(external_id=scheduled_exam.external_id)
        .one_or_none()
    )
    if db_scheduled_exam is None:
        db_scheduled_exam = models.ScheduledExam(
            dbid=None,
            exam_file_info_dbid=db_exam_file_info.dbid,
            external_id=scheduled_exam.external_id,
            exam_title=scheduled_exam.exam_title,
            start_time=scheduled_exam.start_time,
            end_time=scheduled_exam.end_time,
            modified_at=scheduled_exam.modified_at,
        )
        db.add(db_scheduled_exam)
    else:
        db_scheduled_exam.exam_file_info_dbid = db_exam_file_info.dbid
        db_scheduled_exam.exam_title = scheduled_exam.exam_title
        db_scheduled_exam.start_time = scheduled_exam.start_time
        db_scheduled_exam.end_time = scheduled_exam.end_time
        db_scheduled_exam.modified_at = scheduled_exam.modified_at

    return db_scheduled_exam


async def _save_scheduled_exam_package(
    scheduled_exam_package: schemas.ScheduledExamPackage,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
) -> models.ScheduledExamPackage:
    scheduled_exam_external_ids = set(
        scheduled_exam_package.scheduled_exam_external_ids
    )

    db_scheduled_exam_package = (
        db.query(models.ScheduledExamPackage)
        .filter_by(external_id=scheduled_exam_package.external_id)
        .one_or_none()
    )

    if db_scheduled_exam_package is None:
        db_scheduled_exam_package = models.ScheduledExamPackage(
            dbid=None,
            external_id=scheduled_exam_package.external_id,
            start_time=scheduled_exam_package.start_time,
            end_time=scheduled_exam_package.end_time,
            lock_time=scheduled_exam_package.lock_time,
            locked=scheduled_exam_package.locked,
        )
        db.add(db_scheduled_exam_package)
        db.flush()
        db.refresh(db_scheduled_exam_package)
    else:
        # Remove old exam -> package connections
        for existing_db_scheduled_exam in db_scheduled_exam_package.scheduled_exams:
            existing_db_scheduled_exam.scheduled_exam_package_dbid = None

        db_scheduled_exam_package.start_time = scheduled_exam_package.start_time
        db_scheduled_exam_package.end_time = scheduled_exam_package.end_time
        db_scheduled_exam_package.lock_time = scheduled_exam_package.lock_time
        db_scheduled_exam_package.locked = scheduled_exam_package.locked

    for scheduled_exam_external_id in scheduled_exam_external_ids:
        db_scheduled_exam = (
            db.query(models.ScheduledExam)
            .filter_by(external_id=scheduled_exam_external_id)
            .one()
        )
        db_scheduled_exam.scheduled_exam_package_dbid = db_scheduled_exam_package.dbid

    return db_scheduled_exam_package


@router.post(
    "/save_exam_info",
    response_model=None,
    summary="Save exam info",
)
async def _save_exam_info(
    exam_info: schemas.ExamInfo,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    db_exam_info = (
        db.query(models.ExamInfo)
        .filter_by(request_id=exam_info.request_id)
        .one_or_none()
    )
    if db_exam_info is not None:
        raise fastapi.exceptions.HTTPException(
            409, detail=f"exam info {exam_info.request_id} is already saved"
        )

    db.add(
        models.ExamInfo(
            dbid=None,
            request_id=exam_info.request_id,
            raw_data=exam_info.raw_data,
        )
    )

    for scheduled_exam in exam_info.scheduled_exams:
        await _save_scheduled_exam(scheduled_exam, db)

    for scheduled_exam_package in exam_info.scheduled_exam_packages:
        await _save_scheduled_exam_package(scheduled_exam_package, db)

    db.commit()


_VALID_TRANSITIONS = {
    None: "ready",
    "ready": "running",
    "running": "stopping",
    "stopping": "stopped",
    "stopped": "archived",
}


@router.post(
    "/set_current_scheduled_exam_package_state",
    response_model=schemas.ScheduledExamPackageState | None,
    summary="Set current scheduled exam package state",
)
async def _set_current_scheduled_exam_package_state(
    data: schemas.SetCurrentScheduledExamPackageStateData,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    utcnow = ktp_controller.utils.utcnow()

    db_current_scheduled_exam_package = (
        db.query(models.ScheduledExamPackage)
        .filter_by(external_id=data.external_id, current=True)
        .one_or_none()
    )
    if db_current_scheduled_exam_package is None:
        raise fastapi.exceptions.HTTPException(
            409, detail="scheduled exam package is not current"
        )

    try:
        valid_next_state = _VALID_TRANSITIONS[db_current_scheduled_exam_package.state]
    except KeyError as key_error:
        raise fastapi.exceptions.HTTPException(
            409, detail="state of the current scheduled exam package cannot be changed"
        ) from key_error

    if valid_next_state != data.state:
        raise fastapi.exceptions.HTTPException(
            409,
            detail=f"state of the current scheduled exam package cannot be changed to {data.state}",
        )

    old_state = db_current_scheduled_exam_package.state

    if old_state != data.state:
        db_current_scheduled_exam_package.state = data.state
        db_current_scheduled_exam_package.state_changed_at = utcnow
        db.commit()

    return old_state


@router.post(
    "/get_current_scheduled_exam_package",
    response_model=schemas.ScheduledExamPackage | None,
    summary="Get current scheduled exam package",
)
async def _get_current_scheduled_exam_package(
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    utcnow = ktp_controller.utils.utcnow()

    db_current_scheduled_exam_package = (
        db.query(models.ScheduledExamPackage).filter_by(current=True).one_or_none()
    )

    if db_current_scheduled_exam_package is None:
        db_current_scheduled_exam_package = (
            db.query(models.ScheduledExamPackage)
            .filter_by(locked=True)
            .filter_by(state=None)
            .filter(models.ScheduledExamPackage.end_time >= utcnow)
            .order_by(
                sqlalchemy.sql.asc(models.ScheduledExamPackage.start_time),
                sqlalchemy.sql.asc(models.ScheduledExamPackage.dbid),
            )
            .limit(1)
            .one_or_none()
        )

        if db_current_scheduled_exam_package is None:
            return (
                None  # No locked upcoming or ongoing scheduled exam packages available.
            )

        db_current_scheduled_exam_package.current = True
        db.commit()

    return {
        "external_id": db_current_scheduled_exam_package.external_id,
        "start_time": db_current_scheduled_exam_package.start_time.replace(
            tzinfo=datetime.timezone.utc
        ),
        "end_time": db_current_scheduled_exam_package.end_time.replace(
            tzinfo=datetime.timezone.utc
        ),
        "lock_time": None
        if db_current_scheduled_exam_package.lock_time is None
        else db_current_scheduled_exam_package.lock_time.replace(
            tzinfo=datetime.timezone.utc
        ),
        "locked": db_current_scheduled_exam_package.locked,
        "scheduled_exam_external_ids": [
            se.external_id for se in db_current_scheduled_exam_package.scheduled_exams
        ],
        "state": db_current_scheduled_exam_package.state,
        "state_changed_at": None
        if db_current_scheduled_exam_package.state_changed_at is None
        else db_current_scheduled_exam_package.state_changed_at.replace(
            tzinfo=datetime.timezone.utc
        ),
    }


@router.post(
    "/get_scheduled_exam",
    response_model=schemas.ScheduledExam | None,
    summary="Get scheduled exam",
)
async def _get_scheduled_exam(
    data: schemas.GetScheduledExamData,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    db_scheduled_exam = (
        db.query(models.ScheduledExam)
        .filter_by(external_id=data.external_id)
        .one_or_none()
    )

    if db_scheduled_exam is None:
        return None

    return {
        "external_id": db_scheduled_exam.external_id,
        "exam_title": db_scheduled_exam.exam_title,
        "start_time": db_scheduled_exam.start_time.replace(
            tzinfo=datetime.timezone.utc
        ),
        "end_time": db_scheduled_exam.end_time.replace(tzinfo=datetime.timezone.utc),
        "exam_file_info": {
            "external_id": db_scheduled_exam.exam_file_info.external_id,
            "name": db_scheduled_exam.exam_file_info.name,
            "size": db_scheduled_exam.exam_file_info.size,
            "sha256": db_scheduled_exam.exam_file_info.sha256,
            "decrypt_code": db_scheduled_exam.exam_file_info.decrypt_code,
            "modified_at": db_scheduled_exam.exam_file_info.modified_at.replace(
                tzinfo=datetime.timezone.utc
            ),
        },
        "modified_at": db_scheduled_exam.modified_at.replace(
            tzinfo=datetime.timezone.utc
        ),
    }
