# Standard library imports
import datetime
import logging

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

_LOGGER = logging.getLogger(__name__)


class StudentListItem(pydantic.BaseModel):
    name: pydantic.StrictStr
    birthday: datetime.date
    state: pydantic.StrictStr
    last_changed_at: ktp_controller.pydantic.DateTime | None
    exam_title: pydantic.StrictStr | None
