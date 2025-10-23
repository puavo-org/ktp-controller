# Standard library imports
import json
import logging

# Third-party imports
import fastapi  # type: ignore
import fastapi.exceptions  # type: ignore
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql

# Internal imports
from ktp_controller.api.database import get_db
from ktp_controller.api import models

# from ktp_controller.api.database import get_db
from . import schemas


_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["abitti2"])


# How many status reports will ever get stored at most. If this limit
# is hit, then latest _STATUS_REPORT_PRESERVE_COUNT will be
# preserved and all the rest deleted.
_STATUS_REPORT_MAX_COUNT = 35000  # approx. 60 / 5 * 60 * 24 * 2 which means 2 days of reports will be stored, Abitti2 sends one report every 5secs


def _get_status_report_preserve_count():
    # 360 difference, means that delete will hit twice per hour
    # because Abitti2 sends status reports one per 5sec.
    return _STATUS_REPORT_MAX_COUNT - 360  # 60 / 5 * 30 = 360


@router.post(
    "/send_status_report",
    response_model=None,
    summary="Send status report",
)
async def _send_status_report(
    request: schemas.StatusReport,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    status_report_count = db.query(models.Abitti2StatusReport).count()
    if status_report_count >= _STATUS_REPORT_MAX_COUNT:
        delete_subquery = (
            db.query(models.Abitti2StatusReport.dbid)
            .order_by(sqlalchemy.asc(models.Abitti2StatusReport.dbrow_created_at))
            .limit(status_report_count - _get_status_report_preserve_count())
            .subquery()
        )
        db.query(models.Abitti2StatusReport).filter(
            models.Abitti2StatusReport.dbid.in_(sqlalchemy.sql.select(delete_subquery))
        ).delete(synchronize_session="fetch")

    db_status_report = models.Abitti2StatusReport(
        dbid=None, raw_data=json.loads(request.model_dump_json())
    )
    db.add(db_status_report)
    db.commit()
