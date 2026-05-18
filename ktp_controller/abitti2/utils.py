# Standard library imports
import datetime
import logging
import typing

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.schemas
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

        has_finished = (
            student.get("examFinished", False) is True
            or student["sessionStatus"] == "session_ended"
            or student["sessionStatus"].startswith("exam_finished_by_")
        )

        is_waiting_for_auth = student.get("studentStatus", "").startswith(
            "waiting-for-auth"
        )

        exam_title = student.get("examTitle", None)

        flags: {ktp_controller.schemas.StudentFlag} = set()

        if not is_connected:
            flags.add(ktp_controller.schemas.StudentFlag.DISCONNECTED)
        if is_waiting_for_auth:
            flags.add(ktp_controller.schemas.StudentFlag.WAITING_FOR_AUTH)
        if is_idle:
            flags.add(ktp_controller.schemas.StudentFlag.IDLE)
        if exam_title is None:
            flags.add(ktp_controller.schemas.StudentFlag.UNDEFINED_EXAM)

        if has_finished:
            is_active = False
            flags.clear()
        else:
            is_active = len(flags) == 0

        students.append(
            {
                "uuid": student["studentUuid"],
                "session_uuid": student["sessionUuid"],
                "status": student["studentStatus"],
                "is_active": is_active,
                "flags": flags,
                "has_finished": has_finished,
                "exam_title": exam_title,
            }
        )

    return students


def validate_security_code(security_code: typing.Dict[str, str]) -> None:
    """Raise ValueError if security_code is not a well-formed Abitti2 security code dict."""
    if not isinstance(security_code, dict):
        raise ValueError("not dict")
    if set(security_code.keys()) != {"keyCode", "confirmationCode"}:
        raise ValueError("has invalid keys")
    if not isinstance(security_code["keyCode"], str):
        raise ValueError("keyCode is not str")
    if not isinstance(security_code["confirmationCode"], str):
        raise ValueError("confirmationCode is not str")


def security_code_to_student_access_code(
    security_code: typing.Dict[str, str] | None,
) -> ktp_controller.schemas.StudentAccessCode | None:
    """Convert an Abitti2 security code dict to a StudentAccessCode, or None."""
    if security_code is None:
        return None

    return ktp_controller.schemas.StudentAccessCode(
        key_code=security_code["keyCode"],
        verification_code=security_code["confirmationCode"],
    )


def no_active_students(status_report: typing.Dict[str, typing.Any]) -> bool:
    """Return True when there are no active students in the status report.

    >>> no_active_students({"abitti2": {"students": []}})
    True
    >>> no_active_students({"abitti2": {"students": [{"age": 13}]}})
    Traceback (most recent call last):
    ...
    KeyError: 'is_active'
    >>> no_active_students({"abitti2": {"students": [{"is_active": False}]}})
    True
    >>> no_active_students({"abitti2": {"students": [{"is_active": True}, {"is_active": False}]}})
    False
    >>> no_active_students({"abitti2": {"students": [{"is_active": True}, {"is_active": True}]}})
    False
    >>> no_active_students({"abitti2": {"students": [{"is_active": False}, {"is_active": False}]}})
    True
    """
    return all(not s["is_active"] for s in status_report["abitti2"]["students"])


async def allow_students_to_use_browsers(students: typing.List[typing.Dict]) -> None:
    """Grant browser access to every student that is waiting for auth-browser."""
    for student in students:
        student_uuid = student["uuid"]
        session_uuid = student["session_uuid"]
        student_status = student["status"]

        if student_status != "waiting-for-auth-browser":
            continue

        try:
            await ktp_controller.abitti2.client.set_exam_session_permission_to_use_browsers(
                session_uuid, True
            )
        except Exception:
            _LOGGER.error(
                "failed to allow student %s to use browsers in session %s",
                student_uuid,
                session_uuid,
            )
            continue

        _LOGGER.info(
            "allowed student %s to use browsers in session %s",
            student_uuid,
            session_uuid,
        )
