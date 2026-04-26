# Standard library imports
import datetime
import logging
import typing

# Internal imports
import ktp_controller.utils

_LOGGER = logging.getLogger(__file__)


def sanitize_stats_message(stats_message: typing.Dict[str, typing.Any]) -> bool:
    """Best-effort in-place sanitation of Abitti2 stats messages.

    Return boolean indicating whether the stats message was changed or not.

    >>> m = {'data': {'students': [{'id': 1, 'lastName': 'Meikalainen', 'firstNames': 'Matti Henrik'}, {'studentBd': '1234'}]}}
    >>> sanitize_stats_message(m)
    True
    >>> m
    {'data': {'students': [{'id': 1}, {}]}}
    >>> m = {'data': {'students': [{'id': 1}]}}
    >>> sanitize_stats_message(m)
    False
    >>> m
    {'data': {'students': [{'id': 1}]}}
    """
    try:
        data = stats_message["data"]
    except KeyError:
        _LOGGER.warning(
            "Unexpected Abitti2 stats messsage format: 'data' field is missing: %r",
            stats_message,
        )
        return False

    try:
        students = data["students"]
    except KeyError:
        _LOGGER.warning(
            "Unexpected Abitti2 stats messsage format: 'data.students' field is missing: %r",
            stats_message,
        )
        return False

    changed = False

    for i, student in enumerate(students):
        for field_name in ("firstNames", "lastName", "studentBd"):
            try:
                student.pop(field_name)
            except KeyError:
                _LOGGER.warning(
                    "Unexpected Abitti2 stats messsage format: 'data.students[%d].%s' field is missing: %r",
                    i,
                    field_name,
                    stats_message,
                )
                continue
            changed = True

    return changed


def parse_students(
    sanitized_stats_message: typing.Dict[str, typing.Any],
    *,
    utcnow: datetime.datetime | None = None,
) -> typing.List[typing.Dict[str, typing.Any]]:
    if utcnow is None:
        utcnow = ktp_controller.utils.utcnow()

    students = []

    for student in sanitized_stats_message["data"]["students"]:
        is_connected = student.get("isConnected", True)

        is_idle = False
        update_time = student.get("updateTime", None)
        if update_time is not None:
            is_idle = (
                utcnow - datetime.datetime.fromisoformat(update_time)
            ).total_seconds() >= 30 * 60

        is_finished = (
            student.get("examFinished", False) is True
            or student["sessionStatus"] == "session_ended"
            or student["sessionStatus"].startswith("exam_finished_by_")
        )

        is_waiting_for_auth = student.get("studentStatus", "") == "waiting-for-auth"

        is_active = (
            is_connected and not is_idle and not is_finished and not is_waiting_for_auth
        )

        students.append(
            {
                "uuid": student["studentUuid"],
                "session_uuid": student["sessionUuid"],
                "status": student["studentStatus"],
                "is_active": is_active,
                "exam_title": student.get("examTitle", None),
            }
        )

    return students
