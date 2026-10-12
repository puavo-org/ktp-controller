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
    IN_EXAM = "in_exam"
    WAITING = "waiting"
    HAS_PROBLEMS = "has_problems"


class StudentStateCounts(pydantic.BaseModel):
    finished: ktp_controller.pydantic.StrictNonNegativeInt = 0
    in_exam: ktp_controller.pydantic.StrictNonNegativeInt = 0
    waiting: ktp_controller.pydantic.StrictNonNegativeInt = 0
    has_problems: ktp_controller.pydantic.StrictNonNegativeInt = 0

    def total_count(self) -> int:
        return self.finished + self.in_exam + self.waiting + self.has_problems


class StudentListItem(pydantic.BaseModel):
    name: pydantic.StrictStr
    birthday: datetime.date
    state: StudentState
    flags: set[pydantic.StrictStr]
    last_changed_at: ktp_controller.pydantic.DateTime | None
    exam_title: pydantic.StrictStr | None
    student_uuid: pydantic.StrictStr
    session_uuid: pydantic.StrictStr
    is_allowed_to_use_browser: pydantic.StrictBool | None
    last_audio: pydantic.StrictInt | None
    wants_to_use_browser: pydantic.StrictBool


class Exam(pydantic.BaseModel):
    external_id: pydantic.StrictStr
    title: pydantic.StrictStr
    student_state_counts: StudentStateCounts
    started_at: ktp_controller.pydantic.DateTime | None
    scheduled_start_time: ktp_controller.pydantic.DateTime | None
    scheduled_end_time: ktp_controller.pydantic.DateTime | None
