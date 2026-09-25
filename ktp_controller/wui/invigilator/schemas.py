# Standard library imports
import datetime
import enum
import logging

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

_LOGGER = logging.getLogger(__name__)


class StudentState(enum.StrEnum):
    FINISHED = "finished"
    ACTIVE = "active"
    FLAGGED = "flagged"


class StudentListItem(pydantic.BaseModel):
    name: pydantic.StrictStr
    birthday: datetime.date
    state: StudentState
    flags: set[pydantic.StrictStr]
    last_changed_at: ktp_controller.pydantic.DateTime | None
    exam_title: pydantic.StrictStr | None
    student_uuid: pydantic.StrictStr
    session_uuid: pydantic.StrictStr
