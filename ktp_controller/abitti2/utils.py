# Standard library imports
import logging
import typing

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
