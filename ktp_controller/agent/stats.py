# Standard library imports
import abc
import dataclasses

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic


__all__ = [
    "ConnectionStats",
    "ExamomaticConnectionStats",
    "APIConnectionStats",
    "Abitti2ConnectionStats",
]


@dataclasses.dataclass
class ConnectionStats(abc.ABC):
    connected_at: ktp_controller.pydantic.DateTime


class ExamomaticConnectionStats(ConnectionStats):
    ping_pong_count: pydantic.NonNegativeInt = 0
    refresh_exams_count: pydantic.NonNegativeInt = 0
    last_message_received_at: ktp_controller.pydantic.DateTime | None = None


class APIConnectionStats(ConnectionStats):
    pass


class Abitti2ConnectionStats(ConnectionStats):
    pass
