# Standard library imports

# Third-party imports

# Internal imports
import ktp_controller.examomatic.schemas
import ktp_controller.pydantic

# Relative imports


__all__ = [
    "StatusReport",
]


class StatusReport(ktp_controller.examomatic.schemas.StatusReport):
    reported_at: ktp_controller.pydantic.DateTime | None
