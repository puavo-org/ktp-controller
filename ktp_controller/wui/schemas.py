# Standard library imports
import collections.abc
import datetime
import enum
import logging

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

__all__ = [
    "StudentState",
    "StudentStateCounts",
    "StudentListItem",
    "Severity",
    "highest_severity",
]

_LOGGER = logging.getLogger(__name__)


class StudentState(enum.StrEnum):
    FINISHED = "finished"
    IN_EXAM = "in_exam"
    WAITING = "waiting"
    HAS_PROBLEMS = "has_problems"


class Severity(enum.StrEnum):
    """Matches the `value-<severity>` CSS classes in app.css."""

    WARNING = "warning"
    ERROR = "error"


_SEVERITY_RANK = {Severity.WARNING: 1, Severity.ERROR: 2}


def highest_severity(
    severities: collections.abc.Iterable[Severity | None],
) -> Severity | None:
    present = [s for s in severities if s is not None]
    return max(present, key=lambda s: _SEVERITY_RANK[s], default=None)


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
