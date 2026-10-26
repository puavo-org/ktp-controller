# Standard library imports
import logging

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic
import ktp_controller.wui.schemas

_LOGGER = logging.getLogger(__name__)


class Exam(pydantic.BaseModel):
    external_id: pydantic.StrictStr
    title: pydantic.StrictStr
    student_state_counts: ktp_controller.wui.schemas.StudentStateCounts
    started_at: ktp_controller.pydantic.DateTime | None
    scheduled_start_time: ktp_controller.pydantic.DateTime | None
    scheduled_end_time: ktp_controller.pydantic.DateTime | None
